# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date


class HrCandidateCertification(models.Model):
    _name = 'hr.candidate.certification'
    _description = 'Candidate Certification'
    _order = 'issue_date desc, id desc'

    # Relations
    candidate_id = fields.Many2one(
        'hr.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Certification Details
    name = fields.Char(
        string='Certification Name',
        required=True,
        help='Name of the certification (e.g., AWS Certified Solutions Architect)'
    )
    issuer = fields.Char(
        string='Issuing Organization',
        required=True,
        help='Organization that issued the certification'
    )
    credential_id = fields.Char(
        string='Credential ID',
        help='Unique identification number for the certification'
    )
    credential_url = fields.Char(
        string='Credential URL',
        help='URL to verify the certification online'
    )
    
    # Dates
    issue_date = fields.Date(
        string='Issue Date',
        required=True,
        help='Date when the certification was issued'
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        help='Date when the certification expires (leave blank if it does not expire)'
    )
    
    # Computed Fields
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True,
        help='Whether the certification has expired'
    )
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_is_expired',
        store=True,
        help='Whether the certification will expire within 90 days'
    )
    status_display = fields.Char(
        string='Status',
        compute='_compute_status_display',
        store=True
    )
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = date.today()
        for record in self:
            if record.expiry_date:
                record.is_expired = record.expiry_date < today
                days_until_expiry = (record.expiry_date - today).days
                record.is_expiring_soon = 0 < days_until_expiry <= 90
            else:
                record.is_expired = False
                record.is_expiring_soon = False
    
    @api.depends('is_expired', 'is_expiring_soon', 'expiry_date')
    def _compute_status_display(self):
        for record in self:
            if not record.expiry_date:
                record.status_display = 'No Expiration'
            elif record.is_expired:
                record.status_display = 'Expired'
            elif record.is_expiring_soon:
                days = (record.expiry_date - date.today()).days
                record.status_display = f'Expires in {days} days'
            else:
                record.status_display = 'Active'
    
    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for record in self:
            if record.expiry_date and record.issue_date:
                if record.expiry_date < record.issue_date:
                    raise ValidationError(_('Expiry date must be after issue date.'))
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.issuer}"
            if record.status_display:
                name = f"{record.name} - {record.issuer} ({record.status_display})"
            result.append((record.id, name))
        return result
    
    def action_open_credential_url(self):
        """Open the credential verification URL."""
        self.ensure_one()
        if not self.credential_url:
            raise ValidationError(_('No credential URL is set for this certification.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.credential_url,
            'target': 'new',
        }

