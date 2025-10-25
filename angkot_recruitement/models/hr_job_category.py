# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrJobCategory(models.Model):
    _name = 'hr.job.category'
    _description = 'Job Category'
    _order = 'sequence, name'

    name = fields.Char(
        string="Category Name", 
        required=True,
        help="Name of the job category (e.g., Technology, Marketing, Design)"
    )
    
    sequence = fields.Integer(
        string="Sequence", 
        default=10,
        help="Order of appearance in lists"
    )
    
    description = fields.Text(
        string="Description",
        help="Detailed description of this job category"
    )
    
    active = fields.Boolean(
        string="Active", 
        default=True,
        help="Uncheck to hide this category without deleting it"
    )
    
    # Relations
    job_ids = fields.One2many(
        'hr.job', 
        'job_category_id', 
        string="Jobs",
        help="Jobs belonging to this category"
    )
    
    # Computed fields
    job_count = fields.Integer(
        string="Job Count",
        compute='_compute_job_count',
        store=True,
        help="Number of active jobs in this category"
    )
    
    active_job_count = fields.Integer(
        string="Active Job Count",
        compute='_compute_job_count',
        store=True,
        help="Number of active job postings in this category"
    )

    @api.depends('job_ids', 'job_ids.active')
    def _compute_job_count(self):
        for category in self:
            category.job_count = len(category.job_ids)
            category.active_job_count = len(category.job_ids.filtered('active'))

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Enable searching by name"""
        args = args or []
        if name:
            categories = self.search([('name', operator, name)] + args, limit=limit)
            return categories.name_get()
        return super().name_search(name, args, operator, limit)

    def name_get(self):
        """Display name with job count"""
        result = []
        for category in self:
            name = category.name
            if category.active_job_count > 0:
                name = f"{name} ({category.active_job_count})"
            result.append((category.id, name))
        return result
