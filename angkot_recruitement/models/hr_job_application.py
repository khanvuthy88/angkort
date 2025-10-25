from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    """Extend the existing hr.applicant model with job portal specific features"""
    _inherit = 'hr.applicant'
    
    # Job Portal Specific Fields
    portfolio_url = fields.Char(string='Portfolio/Website', help='Candidate portfolio or personal website')
    application_source = fields.Selection([
        ('job_portal', 'Job Portal'),
        ('email', 'Email'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Employee Referral'),
        ('other', 'Other')
    ], string='Application Source', default='job_portal', tracking=True)
    
    # Enhanced notification methods for job portal
    def _send_job_portal_notifications(self):
        """Send email notifications for job portal applications"""
        self.ensure_one()
        
        try:
            # Send confirmation email to applicant
            self._send_applicant_confirmation()
            
            # Send notification email to HR/Recruiter
            self._send_hr_notification()
            
        except Exception as e:
            _logger.error(f"Error sending job portal notifications: {e}")
    
    def _send_applicant_confirmation(self):
        """Send confirmation email to applicant"""
        self.ensure_one()
        
        # Use existing mail template or create fallback
        template = self.env.ref('angkot_recruitement.email_template_job_application_confirmation', False)
        if template:
            template.send_mail(self.id, force_send=True)
        else:
            # Fallback email sending
            mail_values = {
                'subject': f'Application Confirmation - {self.job_id.name}',
                'body_html': f'''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">Application Received</h2>
                    <p>Dear {self.partner_name},</p>
                    <p>Thank you for your interest in the <strong>{self.job_id.name}</strong> position at <strong>{self.job_id.company_id.name}</strong>.</p>
                    <p>We have received your application and our team will review it carefully. We will get back to you within 5-7 business days.</p>
                    <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Application Details:</h3>
                        <p><strong>Position:</strong> {self.job_id.name}</p>
                        <p><strong>Company:</strong> {self.job_id.company_id.name}</p>
                        <p><strong>Application Date:</strong> {self.create_date.strftime('%B %d, %Y')}</p>
                        <p><strong>Status:</strong> {self.stage_id.name if self.stage_id else 'Under Review'}</p>
                    </div>
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                    <p>Best regards,<br>The {self.job_id.company_id.name} Team</p>
                </div>
                ''',
                'email_to': self.email_from,
                'email_from': self.env.user.email or 'noreply@company.com',
                'auto_delete': True,
            }
            self.env['mail.mail'].create(mail_values).send()
    
    def _send_hr_notification(self):
        """Send notification email to HR/Recruiter"""
        self.ensure_one()
        
        # Get HR users or job responsible person
        hr_users = self.job_id.user_id or self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('hr_recruitment.group_hr_recruitment_user').id)
        ])
        
        if not hr_users:
            hr_users = self.env['res.users'].search([('groups_id', 'in', self.env.ref('base.group_user').id)], limit=1)
        
        for user in hr_users:
            mail_values = {
                'subject': f'New Job Application - {self.job_id.name}',
                'body_html': f'''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc2626;">New Job Application</h2>
                    <p>A new application has been submitted for the <strong>{self.job_id.name}</strong> position.</p>
                    <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Applicant Information:</h3>
                        <p><strong>Name:</strong> {self.partner_name}</p>
                        <p><strong>Email:</strong> {self.email_from}</p>
                        <p><strong>Phone:</strong> {self.partner_phone or 'Not provided'}</p>
                        <p><strong>LinkedIn:</strong> {self.linkedin_profile or 'Not provided'}</p>
                        <p><strong>Position:</strong> {self.job_id.name}</p>
                        <p><strong>Application Date:</strong> {self.create_date.strftime('%B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Source:</strong> {dict(self._fields['application_source'].selection)[self.application_source]}</p>
                    </div>
                    <p>Please review the application in the recruitment module.</p>
                    <p>Best regards,<br>Angkot Recruitment System</p>
                </div>
                ''',
                'email_to': user.email,
                'email_from': self.env.user.email or 'noreply@company.com',
                'auto_delete': True,
            }
            self.env['mail.mail'].create(mail_values).send()
    
    @api.model
    def create_from_job_portal(self, job_id, application_data):
        """Create applicant from job portal application data"""
        # Create or find candidate
        candidate = self.env['hr.candidate'].search([
            ('email_from', '=', application_data.get('email'))
        ], limit=1)
        
        if not candidate:
            candidate = self.env['hr.candidate'].create({
                'partner_name': application_data.get('applicant_name'),
                'email_from': application_data.get('email'),
                'partner_phone': application_data.get('phone', ''),
                'linkedin_profile': application_data.get('linkedin_url', ''),
            })
        
        # Create applicant
        applicant_vals = {
            'candidate_id': candidate.id,
            'job_id': job_id,
            'application_source': 'job_portal',
            'portfolio_url': application_data.get('portfolio_url', ''),
        }
        
        # Handle resume attachment
        if application_data.get('resume_file'):
            attachment_vals = {
                'name': application_data.get('resume_filename', 'resume.pdf'),
                'type': 'binary',
                'datas': application_data['resume_file'],
                'res_model': 'hr.applicant',
                'res_id': 0,  # Will be updated after creation
            }
            # We'll create the attachment after the applicant is created
        
        applicant = self.create(applicant_vals)
        
        # Create resume attachment if provided
        if application_data.get('resume_file'):
            attachment_vals['res_id'] = applicant.id
            self.env['ir.attachment'].create(attachment_vals)
        
        # Send notifications
        applicant._send_job_portal_notifications()
        
        return applicant
