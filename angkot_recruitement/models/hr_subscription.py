# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HrSubscription(models.Model):
    _name = 'hr.subscription'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'sequence.mixin']
    _description = 'Job Portal Subscription'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(string='Subscription Name', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='user_id.partner_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related='user_id.company_id', store=True, readonly=True)
    
    # Plan Information
    plan_id = fields.Selection([
        ('basic', 'Basic Plan'),
        ('premium', 'Premium Plan'),
        ('enterprise', 'Enterprise Plan')
    ], string='Plan', required=True, default='basic')
    
    plan_name = fields.Char(string='Plan Name', compute='_compute_plan_info', store=True)
    plan_price = fields.Float(string='Plan Price', compute='_compute_plan_info', store=True)
    
    # Subscription Details
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending_payment', 'Pending Payment'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trial', 'Trial')
    ], string='Status', default='trial', required=True)
    
    billing_cycle = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string='Billing Cycle', required=True, default='monthly')
    
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date(string='End Date', required=True)
    date = fields.Date(compute="compute_date", store=True)
    auto_renew = fields.Boolean(string='Auto Renewal', default=True)
    
    # Pricing
    price = fields.Float(string='Price', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    discount_percentage = fields.Float(string='Discount %', default=0.0)
    discounted_price = fields.Float(string='Discounted Price', compute='_compute_discounted_price', store=True)
    
    # Features
    max_jobs = fields.Integer(string='Max Job Postings', required=True, default=5)
    job_boost = fields.Boolean(string='Job Boost', default=False)
    priority_support = fields.Boolean(string='Priority Support', default=False)
    analytics = fields.Boolean(string='Advanced Analytics', default=True)
    custom_branding = fields.Boolean(string='Custom Branding', default=False)
    
    # Payment Information
    payment_method = fields.Selection([
        ('card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('khqr', 'KHQR (Bakong)')
    ], string='Payment Method', default='card')
    
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='pending')
    
    payment_date = fields.Datetime(string='Payment Date')
    payment_reference = fields.Char(string='Payment Reference')
    
    # Invoice Information
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    
    # KHQR Payment Fields
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account', 
                                       domain="[('partner_id', '=', company_id), ('country_code', '=', 'KH')]")
    qr_code_data = fields.Char(string='QR Code Data', readonly=True, copy=False)
    qr_code_image = fields.Binary(string='QR Code Image', readonly=True, copy=False, attachment=True)
    qr_code_url = fields.Char(string='QR Code URL', compute='_compute_qr_code_url')
    show_qr_code = fields.Boolean(string='Show QR Code', compute='_compute_show_qr_code')
    
    # Additional Information
    notes = fields.Text(string='Notes')
    trial_end_date = fields.Date(string='Trial End Date')
    is_trial = fields.Boolean(string='Is Trial', default=True)
    
    # Computed Fields
    days_remaining = fields.Integer(string='Days Remaining', compute='_compute_days_remaining')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    display_name = fields.Char(string='Display Name', compute='_compute_display_name')

    @api.depends('start_date')
    def compute_date(self):
        for rec in self:
            rec.date = rec.start_date
    
    @api.depends('invoice_id')
    def _compute_invoice_count(self):
        """Compute invoice count"""
        for record in self:
            record.invoice_count = 1 if record.invoice_id else 0
    
    @api.depends('payment_method', 'payment_status', 'qr_code_data')
    def _compute_show_qr_code(self):
        """Determine if QR code should be shown"""
        for record in self:
            record.show_qr_code = (
                record.payment_method == 'khqr' and 
                record.payment_status == 'pending' and 
                bool(record.qr_code_data)
            )
    
    @api.depends('qr_code_data')
    def _compute_qr_code_url(self):
        """Generate QR code URL for API access"""
        for record in self:
            if record.qr_code_data and record.id:
                base_url = record.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.qr_code_url = f"{base_url}/web/image/hr.subscription/{record.id}/qr_code_image"
            else:
                record.qr_code_url = False
    
    @api.depends('plan_id')
    def _compute_plan_info(self):
        """Compute plan name and price based on plan_id"""
        plan_info = {
            'basic': {'name': 'Basic Plan', 'price': 99.0},
            'premium': {'name': 'Premium Plan', 'price': 299.0},
            'enterprise': {'name': 'Enterprise Plan', 'price': 599.0}
        }
        
        for record in self:
            info = plan_info.get(record.plan_id, {'name': 'Unknown Plan', 'price': 0.0})
            record.plan_name = info['name']
            record.plan_price = info['price']
            record.price = info['price']
    
    @api.depends('price', 'discount_percentage')
    def _compute_discounted_price(self):
        """Compute discounted price"""
        for record in self:
            if record.discount_percentage > 0:
                discount_amount = (record.price * record.discount_percentage) / 100
                record.discounted_price = record.price - discount_amount
            else:
                record.discounted_price = record.price
    
    @api.depends('end_date')
    def _compute_days_remaining(self):
        """Compute days remaining until subscription expires"""
        today = fields.Date.today()
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_remaining = delta.days if delta.days >= 0 else 0
            else:
                record.days_remaining = 0
    
    @api.depends('end_date', 'status')
    def _compute_is_expired(self):
        """Check if subscription is expired"""
        today = fields.Date.today()
        for record in self:
            record.is_expired = (
                record.end_date and 
                record.end_date < today and 
                record.status not in ['cancelled', 'expired']
            )
    
    @api.depends('plan_name', 'user_id', 'status')
    def _compute_display_name(self):
        """Compute display name for the record"""
        for record in self:
            if record.plan_name and record.user_id:
                record.display_name = f"{record.plan_name} - {record.user_id.name} ({record.status})"
            else:
                record.display_name = record.name
    
    @api.model_create_multi
    def create(self, vals):
        """Override create to set sequence and end date"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.subscription') or _('New')
        
        # Set end date based on billing cycle if not provided
        if 'end_date' not in vals:
            # Get start_date from vals or use default (today)
            start_date = vals.get('start_date')
            if isinstance(start_date, str):
                start_date = fields.Date.from_string(start_date)
            elif start_date is None:
                start_date = fields.Date.today()
            
            # Get billing cycle from vals or use default (monthly)
            billing_cycle = vals.get('billing_cycle', 'monthly')
            
            # Calculate end date
            if billing_cycle == 'yearly':
                end_date = start_date + timedelta(days=365)
            else:  # monthly
                end_date = start_date + timedelta(days=30)
            
            vals['end_date'] = end_date
        
        # Set max jobs and price based on plan
        if 'plan_id' in vals:
            plan_info = {
                'basic': {'max_jobs': 5, 'price': 99.0},
                'premium': {'max_jobs': 20, 'price': 299.0},
                'enterprise': {'max_jobs': -1, 'price': 599.0}  # Unlimited
            }
            info = plan_info.get(vals['plan_id'], {'max_jobs': 5, 'price': 99.0})
            
            if 'max_jobs' not in vals:
                vals['max_jobs'] = info['max_jobs']
            
            if 'price' not in vals:
                vals['price'] = info['price']
        
        return super(HrSubscription, self).create(vals)
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate start and end dates"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError(_('End date must be after start date.'))
    
    @api.constrains('price')
    def _check_price(self):
        """Validate price is positive"""
        for record in self:
            if record.price < 0:
                raise ValidationError(_('Price must be positive.'))
    
    def action_activate(self):
        """Activate subscription"""
        for record in self:
            if record.status in ['pending_payment', 'trial']:
                record.status = 'active'
                record.payment_status = 'paid'
                record.payment_date = fields.Datetime.now()
                _logger.info(f"Subscription {record.name} activated for user {record.user_id.name}")
    
    def action_cancel(self):
        """Cancel subscription"""
        for record in self:
            record.status = 'cancelled'
            record.auto_renew = False
            _logger.info(f"Subscription {record.name} cancelled for user {record.user_id.name}")
    
    def action_expire(self):
        """Expire subscription"""
        for record in self:
            record.status = 'expired'
            record.auto_renew = False
            _logger.info(f"Subscription {record.name} expired for user {record.user_id.name}")
    
    def renew_subscription(self):
        """Renew subscription for another billing cycle"""
        for record in self:
            if record.status == 'active' and record.auto_renew:
                # Extend end date
                current_end_date = record.end_date
                if record.billing_cycle == 'yearly':
                    new_end_date = current_end_date + timedelta(days=365)
                else:  # monthly
                    new_end_date = current_end_date + timedelta(days=30)
                
                record.end_date = new_end_date
                record.payment_status = 'pending'  # Reset payment status for new billing cycle
                _logger.info(f"Subscription {record.name} renewed until {new_end_date} for user {record.user_id.name}")
    
    @api.model
    def check_expired_subscriptions(self):
        """Cron job to check and expire subscriptions"""
        today = fields.Date.today()
        expired_subscriptions = self.search([
            ('end_date', '<', today),
            ('status', 'in', ['active', 'trial'])
        ])
        
        for subscription in expired_subscriptions:
            subscription.action_expire()
        
        _logger.info(f"Checked {len(expired_subscriptions)} expired subscriptions")
    
    @api.model
    def get_user_subscription(self, user_id):
        """Get active subscription for a user"""
        return self.search([
            ('user_id', '=', user_id),
            ('status', '=', 'active')
        ], limit=1)
    
    @api.model
    def create_subscription(self, user_id, plan_id, billing_cycle='monthly', payment_method='card'):
        """Create a new subscription for a user"""
        # Check if user already has an active subscription
        existing = self.get_user_subscription(user_id)
        if existing:
            raise UserError(_('User already has an active subscription.'))
        
        # Create new subscription
        subscription = self.create({
            'user_id': user_id,
            'plan_id': plan_id,
            'billing_cycle': billing_cycle,
            'payment_method': payment_method,
            'status': 'pending_payment',
            'is_trial': True,
            'trial_end_date': fields.Date.today() + timedelta(days=14)  # 14-day trial
        })
        
        return subscription
    
    def get_plan_features(self):
        """Get features for the current plan"""
        features = {
            'basic': {
                'max_jobs': 5,
                'job_boost': False,
                'priority_support': False,
                'analytics': True,
                'custom_branding': False
            },
            'premium': {
                'max_jobs': 20,
                'job_boost': True,
                'priority_support': True,
                'analytics': True,
                'custom_branding': False
            },
            'enterprise': {
                'max_jobs': -1,  # Unlimited
                'job_boost': True,
                'priority_support': True,
                'analytics': True,
                'custom_branding': True
            }
        }
        return features.get(self.plan_id, features['basic'])
    
    def can_post_job(self):
        """Check if user can post a job based on subscription limits"""
        if self.status != 'active':
            return False, _('Subscription is not active.')
        
        # Get current job count for user
        job_count = self.env['hr.job'].search_count([
            ('user_id', '=', self.user_id.id),
            ('active', '=', True)
        ])
        
        if self.max_jobs == -1:  # Unlimited
            return True, _('Can post unlimited jobs.')
        
        if job_count >= self.max_jobs:
            return False, _('Job posting limit reached for current plan.')
        
        return True, _('Can post job.')
    
    def action_view_invoice(self):
        """View invoice"""
        self.ensure_one()
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }
    
    def action_generate_invoice(self):
        """Generate invoice for subscription"""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_('Invoice already exists for this subscription.'))
        
        # Create invoice
        invoice_vals = self._prepare_invoice()
        invoice = self.env['account.move'].create(invoice_vals)
        
        self.invoice_id = invoice.id
        
        _logger.info(f"Invoice {invoice.name} generated for subscription {self.name}")
        
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }
    
    def _prepare_invoice(self):
        """Prepare invoice values"""
        self.ensure_one()
        
        # Get journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not journal:
            raise UserError(_('Please configure a sales journal for this company.'))
        
        # Get invoice line account
        account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not account:
            raise UserError(_('Please configure an income account for this company.'))
        
        # Prepare invoice line
        invoice_line_vals = {
            'name': f'{self.plan_name} - {self.billing_cycle.title()} Subscription',
            'quantity': 1,
            'price_unit': self.discounted_price,
            'account_id': account.id,
        }
        
        # Prepare invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, invoice_line_vals)],
            'narration': f'Subscription: {self.name}\nPlan: {self.plan_name}\nBilling Cycle: {self.billing_cycle.title()}',
        }
        
        # Add bank account if KHQR payment
        if self.payment_method == 'khqr' and self.partner_bank_id:
            invoice_vals['partner_bank_id'] = self.partner_bank_id.id
        
        return invoice_vals
    
    def action_generate_khqr(self):
        """Generate KHQR code for payment"""
        self.ensure_one()
        
        if self.payment_method != 'khqr':
            raise UserError(_('Payment method must be KHQR to generate QR code.'))
        
        if not self.partner_bank_id:
            raise UserError(_('Please select a bank account for KHQR payment.'))
        
        # Generate or use existing invoice
        if not self.invoice_id:
            self.action_generate_invoice()
        
        # Generate QR code using invoice
        try:
            qr_code_data = self.partner_bank_id._get_qr_vals(
                qr_method='emv_qr',
                amount=self.discounted_price,
                currency=self.currency_id,
                debtor_partner=self.partner_id,
                free_communication=f'Subscription: {self.name}',
                structured_communication=self.name
            )
            
            # Generate QR code image
            qr_code_params = self.partner_bank_id._get_qr_code_generation_params(
                qr_method='emv_qr',
                amount=self.discounted_price,
                currency=self.currency_id,
                debtor_partner=self.partner_id,
                free_communication=f'Subscription: {self.name}',
                structured_communication=self.name
            )
            
            # Generate QR code using barcode module
            import io
            import base64
            try:
                from odoo.tools import barcode
                qr_code_bytes = barcode(
                    qr_code_params['barcode_type'],
                    qr_code_data,
                    width=qr_code_params['width'],
                    height=qr_code_params['height'],
                    humanreadable=qr_code_params['humanreadable']
                )
                qr_code_image = base64.b64encode(qr_code_bytes)
            except Exception as e:
                _logger.warning(f"Error generating QR code image: {e}")
                qr_code_image = False
            
            self.qr_code_data = qr_code_data
            self.qr_code_image = qr_code_image
            
            _logger.info(f"KHQR code generated for subscription {self.name}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('KHQR code generated successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error generating KHQR code: {e}")
            raise UserError(_('Error generating KHQR code: %s') % str(e))
    
    def action_mark_as_paid(self):
        """Mark payment as paid"""
        self.ensure_one()
        
        if self.payment_status == 'paid':
            raise UserError(_('Payment is already marked as paid.'))
        
        self.payment_status = 'paid'
        self.payment_date = fields.Datetime.now()
        
        # Activate subscription if pending payment
        if self.status == 'pending_payment':
            self.status = 'active'
        
        # Mark invoice as paid
        if self.invoice_id and self.invoice_id.state == 'posted':
            # Register payment
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_id.id,
                'amount': self.discounted_price,
                'currency_id': self.currency_id.id,
                'date': fields.Date.today(),
                'journal_id': self.env['account.journal'].search([
                    ('type', 'in', ['bank', 'cash']),
                    ('company_id', '=', self.company_id.id)
                ], limit=1).id,
                'payment_method_line_id': self.env['account.payment.method.line'].search([
                    ('payment_type', '=', 'inbound'),
                ], limit=1).id,
            }
            
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()
            
            # Reconcile with invoice
            self.invoice_id.js_assign_outstanding_line(payment.line_ids.filtered(lambda l: l.account_id == self.invoice_id.line_ids.account_id).id)
        
        _logger.info(f"Subscription {self.name} marked as paid")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payment marked as paid successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }
