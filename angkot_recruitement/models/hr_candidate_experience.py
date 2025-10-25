# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrCandidateExperience(models.Model):
    _name = 'hr.candidate.experience'
    _description = 'Candidate Work Experience'
    _order = 'start_date desc, id desc'

    # Relations
    candidate_id = fields.Many2one(
        'hr.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Experience Details
    company = fields.Char(
        string='Company',
        required=True,
        help='Name of the company or organization'
    )
    position = fields.Char(
        string='Position/Title',
        required=True,
        help='Your job title or position'
    )
    location = fields.Char(
        string='Location',
        help='City, State/Country where you worked'
    )
    employment_type = fields.Selection([
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
        ('remote', 'Remote'),
    ], string='Employment Type', default='full_time')
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        help='When did you start this position'
    )
    end_date = fields.Date(
        string='End Date',
        help='When did you leave this position'
    )
    is_current = fields.Boolean(
        string='Currently Working',
        default=False,
        help='Check if you are currently working in this position'
    )
    
    # Job Details
    description = fields.Text(
        string='Job Description',
        required=True,
        help='Describe your role, responsibilities, and key accomplishments'
    )
    achievements = fields.Text(
        string='Key Achievements',
        help='List specific achievements, metrics, or results you achieved in this role'
    )
    
    # Computed Fields
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display',
        store=True
    )
    duration_months = fields.Integer(
        string='Duration (Months)',
        compute='_compute_duration_months',
        store=True
    )
    
    @api.depends('start_date', 'end_date', 'is_current')
    def _compute_duration_display(self):
        for record in self:
            if record.start_date:
                start = record.start_date.strftime('%b %Y')
                if record.is_current:
                    record.duration_display = f"{start} - Present"
                elif record.end_date:
                    end = record.end_date.strftime('%b %Y')
                    record.duration_display = f"{start} - {end}"
                else:
                    record.duration_display = start
            else:
                record.duration_display = ''
    
    @api.depends('start_date', 'end_date', 'is_current')
    def _compute_duration_months(self):
        for record in self:
            if record.start_date:
                end = fields.Date.today() if record.is_current else record.end_date
                if end:
                    delta = relativedelta(end, record.start_date)
                    record.duration_months = delta.years * 12 + delta.months
                else:
                    record.duration_months = 0
            else:
                record.duration_months = 0
    
    @api.constrains('start_date', 'end_date', 'is_current')
    def _check_dates(self):
        for record in self:
            if not record.is_current and record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError(_('End date must be after start date.'))
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.position} at {record.company}"
            if record.duration_display:
                name = f"{record.position} at {record.company} ({record.duration_display})"
            result.append((record.id, name))
        return result

