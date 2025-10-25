# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrCandidateEducation(models.Model):
    _name = 'hr.candidate.education'
    _description = 'Candidate Education'
    _order = 'start_date desc, id desc'

    # Relations
    candidate_id = fields.Many2one(
        'hr.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Education Details
    school = fields.Char(
        string='School/University',
        required=True,
        help='Name of the educational institution'
    )
    degree = fields.Selection([
        ('high_school', 'High School Diploma'),
        ('associate', 'Associate Degree'),
        ('bachelor_arts', 'Bachelor of Arts (BA)'),
        ('bachelor_science', 'Bachelor of Science (BS)'),
        ('bachelor_engineering', 'Bachelor of Engineering (BE)'),
        ('bachelor_technology', 'Bachelor of Technology (BTech)'),
        ('master_arts', 'Master of Arts (MA)'),
        ('master_science', 'Master of Science (MS)'),
        ('master_business', 'Master of Business Administration (MBA)'),
        ('master_engineering', 'Master of Engineering (ME)'),
        ('master_technology', 'Master of Technology (MTech)'),
        ('doctorate_philosophy', 'Doctor of Philosophy (PhD)'),
        ('doctorate_medicine', 'Doctor of Medicine (MD)'),
        ('juris_doctor', 'Juris Doctor (JD)'),
        ('other', 'Other'),
    ], string='Degree', required=True)
    
    field_of_study = fields.Char(
        string='Field of Study',
        help='Major or area of study (e.g., Computer Science, Business Administration)'
    )
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        help='When did you start this education'
    )
    end_date = fields.Date(
        string='End Date',
        help='When did you complete (or expect to complete) this education'
    )
    is_current = fields.Boolean(
        string='Currently Studying',
        default=False,
        help='Check if you are currently pursuing this education'
    )
    
    # Additional Info
    description = fields.Text(
        string='Description',
        help='Additional details about your education (GPA, honors, relevant coursework, etc.)'
    )
    gpa = fields.Float(
        string='GPA',
        help='Grade Point Average'
    )
    
    # Computed Fields
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display',
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
    
    @api.constrains('start_date', 'end_date', 'is_current')
    def _check_dates(self):
        for record in self:
            if not record.is_current and record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError(_('End date must be after start date.'))
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.degree} - {record.school}"
            if record.field_of_study:
                name = f"{record.degree} in {record.field_of_study} - {record.school}"
            result.append((record.id, name))
        return result

