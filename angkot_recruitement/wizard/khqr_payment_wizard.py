# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class KHQRPaymentWizard(models.TransientModel):
    _name = 'khqr.payment.wizard'
    _description = 'KHQR Payment Wizard'

    subscription_id = fields.Many2one('hr.subscription', string='Subscription', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='subscription_id.partner_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related='subscription_id.company_id', readonly=True)
    
    # Payment Information
    amount = fields.Float(string='Amount', related='subscription_id.discounted_price', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='subscription_id.currency_id', readonly=True)
    
    # Bank Account
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account', 
                                       domain="[('partner_id.id', 'in', [company_id, False]), ('country_code', '=', 'KH')]",
                                       required=True)
    
    # QR Code Information
    qr_code_data = fields.Char(string='QR Code Data', readonly=True)
    qr_code_image = fields.Binary(string='QR Code Image', readonly=True, attachment=True)
    
    # Invoice
    invoice_id = fields.Many2one('account.move', string='Invoice', related='subscription_id.invoice_id', readonly=True)
    
    def action_generate_qr_code(self):
        """Generate KHQR QR code"""
        self.ensure_one()
        
        if not self.partner_bank_id:
            raise UserError(_('Please select a bank account for KHQR payment.'))
        
        # Check if bank account is configured for KHQR
        if self.partner_bank_id.country_code != 'KH':
            raise UserError(_('Selected bank account must be a Cambodian (KH) bank account.'))
        
        if self.partner_bank_id.proxy_type not in ['bakong_id_solo', 'bakong_id_merchant']:
            raise UserError(_('Selected bank account must have a Bakong ID proxy type.'))
        
        # Generate or use existing invoice
        subscription = self.subscription_id
        if not subscription.invoice_id:
            subscription.action_generate_invoice()
        
        # Update subscription bank account
        subscription.partner_bank_id = self.partner_bank_id.id
        
        # Generate QR code
        try:
            qr_code_data = self.partner_bank_id._get_qr_vals(
                qr_method='emv_qr',
                amount=self.amount,
                currency=self.currency_id,
                debtor_partner=self.partner_id,
                free_communication=f'Subscription: {subscription.name}',
                structured_communication=subscription.name
            )
            
            # Generate QR code image
            qr_code_params = self.partner_bank_id._get_qr_code_generation_params(
                qr_method='emv_qr',
                amount=self.amount,
                currency=self.currency_id,
                debtor_partner=self.partner_id,
                free_communication=f'Subscription: {subscription.name}',
                structured_communication=subscription.name
            )
            
            # Generate QR code using barcode module
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
            
            # Update wizard
            self.qr_code_data = qr_code_data
            self.qr_code_image = qr_code_image
            
            # Update subscription
            subscription.qr_code_data = qr_code_data
            subscription.qr_code_image = qr_code_image
            
            _logger.info(f"KHQR code generated for subscription {subscription.name}")
            
            # Return to wizard with generated QR code
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'khqr.payment.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': self.env.context,
            }
            
        except Exception as e:
            _logger.error(f"Error generating KHQR code: {e}")
            raise UserError(_('Error generating KHQR code: %s') % str(e))
    
    def action_confirm_payment(self):
        """Confirm that payment has been made"""
        self.ensure_one()
        
        # Close wizard and return to subscription
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.subscription',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
            'target': 'current',
        }
    
    def action_cancel(self):
        """Cancel wizard"""
        return {'type': 'ir.actions.act_window_close'}

