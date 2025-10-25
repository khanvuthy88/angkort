# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class HrCandidatePortfolio(models.Model):
    _name = 'hr.candidate.portfolio'
    _description = 'Candidate Portfolio Project'
    _order = 'sequence, id desc'

    # Relations
    candidate_id = fields.Many2one(
        'hr.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Portfolio Details
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order in which projects are displayed'
    )
    title = fields.Char(
        string='Project Title',
        required=True,
        help='Name of the project (e.g., E-commerce Platform, Mobile App)'
    )
    description = fields.Text(
        string='Description',
        required=True,
        help='Brief description of the project, your role, and key features'
    )
    url = fields.Char(
        string='Project URL',
        required=True,
        help='Link to the project (GitHub, live demo, etc.)'
    )
    image_url = fields.Char(
        string='Project Image URL',
        help='URL to a screenshot or image of the project'
    )
    
    # Image field (stored locally if needed)
    image = fields.Image(
        string='Project Image',
        max_width=1920,
        max_height=1080,
        help='Upload a screenshot or image of your project'
    )
    
    # Technologies/Tags
    tag_ids = fields.Many2many(
        'hr.candidate.portfolio.tag',
        'portfolio_tag_rel',
        'portfolio_id',
        'tag_id',
        string='Technologies'
    )
    tags_display = fields.Char(
        string='Technology List',
        compute='_compute_tags_display',
        store=True,
        help='Comma-separated list of technologies'
    )
    
    # Project Type
    project_type = fields.Selection([
        ('web', 'Web Application'),
        ('mobile', 'Mobile Application'),
        ('desktop', 'Desktop Application'),
        ('api', 'API/Backend'),
        ('library', 'Library/Package'),
        ('data', 'Data Science/ML'),
        ('design', 'Design/UI/UX'),
        ('other', 'Other'),
    ], string='Project Type', default='web')
    
    # Project Status
    status = fields.Selection([
        ('completed', 'Completed'),
        ('ongoing', 'Ongoing'),
        ('maintenance', 'In Maintenance'),
        ('archived', 'Archived'),
    ], string='Status', default='completed')
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        help='When you started working on this project'
    )
    end_date = fields.Date(
        string='End/Launch Date',
        help='When the project was completed or launched'
    )
    
    # Computed Fields
    url_domain = fields.Char(
        string='Domain',
        compute='_compute_url_domain',
        store=True,
        help='Extracted domain from the URL'
    )
    
    @api.depends('tag_ids', 'tag_ids.name')
    def _compute_tags_display(self):
        for record in self:
            if record.tag_ids:
                record.tags_display = ', '.join(record.tag_ids.mapped('name'))
            else:
                record.tags_display = ''
    
    @api.depends('url')
    def _compute_url_domain(self):
        for record in self:
            if record.url:
                # Extract domain from URL
                match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', record.url)
                if match:
                    record.url_domain = match.group(1)
                else:
                    record.url_domain = ''
            else:
                record.url_domain = ''
    
    @api.constrains('url')
    def _check_url(self):
        for record in self:
            if record.url and not re.match(r'^https?://', record.url):
                # Auto-add https:// if missing
                record.url = f"https://{record.url}"
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError(_('End date must be after start date.'))
    
    def name_get(self):
        result = []
        for record in self:
            name = record.title
            if record.project_type:
                type_label = dict(self._fields['project_type'].selection).get(record.project_type, '')
                name = f"{record.title} ({type_label})"
            result.append((record.id, name))
        return result
    
    def action_open_project_url(self):
        """Open the project URL in a new tab."""
        self.ensure_one()
        if not self.url:
            raise ValidationError(_('No project URL is set.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }


class HrCandidatePortfolioTag(models.Model):
    _name = 'hr.candidate.portfolio.tag'
    _description = 'Portfolio Technology Tag'
    _order = 'name'

    name = fields.Char(
        string='Technology',
        required=True,
        help='Technology or tool name (e.g., React, Python, Docker)'
    )
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color index for visual representation'
    )
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'This technology tag already exists!')
    ]
    
    def name_get(self):
        return [(tag.id, tag.name) for tag in self]

