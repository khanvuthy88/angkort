# -*- coding: utf-8 -*-

from odoo import models, fields, api
import secrets
from datetime import datetime, timedelta


class ResUsers(models.Model):
    _inherit = 'res.users'

    email_verification_token = fields.Char(
        string='Email Verification Token',
        copy=False,
        help='Token used for email verification'
    )
    email_verification_token_expiry = fields.Datetime(
        string='Token Expiry',
        copy=False,
        help='Expiry time for the verification token'
    )
    email_verified = fields.Boolean(
        string='Email Verified',
        default=False,
        copy=False,
        help='Indicates if the user has verified their email address'
    )
    email_verified_date = fields.Datetime(
        string='Email Verified Date',
        copy=False,
        readonly=True,
        help='Date when email was verified'
    )
    candidate_id = fields.Many2one(
        'hr.candidate',
        string='Candidate Profile',
        copy=False,
        help='Link to the candidate profile for job applicants'
    )
    
    # Computed fields for better display
    has_candidate_profile = fields.Boolean(
        string='Has Candidate Profile',
        compute='_compute_has_candidate_profile',
        store=True,
        help='Indicates if this user has an associated candidate profile'
    )
    
    candidate_name = fields.Char(
        string='Candidate Name',
        related='candidate_id.partner_name',
        readonly=True,
        help='Name from the candidate profile'
    )
    
    candidate_email = fields.Char(
        string='Candidate Email',
        related='candidate_id.email_from',
        readonly=True,
        help='Email from the candidate profile'
    )
    
    candidate_phone = fields.Char(
        string='Candidate Phone',
        related='candidate_id.partner_phone',
        readonly=True,
        help='Phone from the candidate profile'
    )
    
    @api.depends('candidate_id')
    def _compute_has_candidate_profile(self):
        """Compute whether user has a candidate profile"""
        for user in self:
            user.has_candidate_profile = bool(user.candidate_id)
    
    def action_view_candidate_profile(self):
        """Action to view the candidate profile"""
        self.ensure_one()
        if not self.candidate_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Candidate Profile',
                    'message': 'This user does not have an associated candidate profile.',
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Candidate Profile',
            'res_model': 'hr.candidate',
            'res_id': self.candidate_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def generate_verification_token(self):
        """Generate a secure verification token"""
        self.ensure_one()
        # Generate a secure random token (32 bytes = 64 hex characters)
        token = secrets.token_urlsafe(32)
        
        # Set token and expiry (24 hours from now)
        self.email_verification_token = token
        self.email_verification_token_expiry = datetime.now() + timedelta(hours=24)
        
        return token

    def verify_email_with_token(self, token):
        """Verify email using the provided token"""
        self.ensure_one()
        
        # Check if token matches and hasn't expired
        if (self.email_verification_token == token and 
            self.email_verification_token_expiry and 
            self.email_verification_token_expiry > datetime.now()):
            
            # Mark email as verified
            self.email_verified = True
            self.email_verified_date = fields.Datetime.now()
            
            # Activate the user
            self.active = True
            
            # Clear the token
            self.email_verification_token = False
            self.email_verification_token_expiry = False
            
            return True
        
        return False

    def send_verification_email(self, base_url):
        """Send verification email to the user"""
        self.ensure_one()
        
        # Generate token
        token = self.generate_verification_token()
        
        # Generate verification URL
        verification_url = f"{base_url}/verify-email?token={token}&email={self.email}"
        
        # Get email template
        template = self.env.ref('angkot_recruitement.email_verification_template', raise_if_not_found=False)
        
        if template:
            # Use template if it exists
            template.with_context(
                verification_url=verification_url,
                user_name=self.name,
            ).send_mail(self.id, force_send=True)
        else:
            # Fallback: Send simple email
            mail_values = {
                'subject': 'Verify Your Email Address',
                'body_html': f'''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #333;">Welcome to Angkot Recruitment!</h2>
                        <p>Hi {self.name},</p>
                        <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{verification_url}" 
                               style="background-color: #4CAF50; color: white; padding: 12px 30px; 
                                      text-decoration: none; border-radius: 5px; display: inline-block;">
                                Verify Email Address
                            </a>
                        </div>
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #666;">{verification_url}</p>
                        <p style="color: #666; font-size: 12px; margin-top: 30px;">
                            This link will expire in 24 hours. If you didn't create an account, please ignore this email.
                        </p>
                    </div>
                ''',
                'email_to': self.email,
                'email_from': self.env.company.email or 'noreply@angkot.com',
                'auto_delete': True,
            }
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        
        return True

    @api.model
    def verify_email_by_token(self, token, email):
        """Public method to verify email by token"""
        user = self.sudo().search([('email', '=', email), ('email_verification_token', '=', token)], limit=1)
        
        if user:
            return user.verify_email_with_token(token)
        
        return False

