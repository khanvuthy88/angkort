# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    # Job Portal Specific Fields
    is_featured = fields.Boolean(
        string="Featured Job",
        default=False,
        help="Mark this job as featured to highlight it on the job portal"
    )

    is_urgent = fields.Boolean(
        string="Urgent Job",
        default=False,
        help="Mark this job as urgent to show urgency indicator"
    )

    job_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
        ('temporary', 'Temporary')
    ], string="Job Type", default='full_time', required=True,
       help="Type of employment for this position")

    experience_level = fields.Selection([
        ('entry_level', 'Entry Level'),
        ('mid_level', 'Mid Level'),
        ('senior_level', 'Senior Level'),
        ('executive', 'Executive')
    ], string="Experience Level", default='entry_level',
       help="Required experience level for this position")

    education_level = fields.Selection([
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor Degree'),
        ('master', 'Master Degree'),
        ('phd', 'PhD')
    ], string="Education Level", default='bachelor',
       help="Required education level for this position")

    # Salary Management
    salary_type = fields.Selection([
        ('range', 'Salary Range'),
        ('fixed', 'Fixed Salary'),
        ('negotiable', 'Negotiable')
    ], string="Salary Type", default='range',
       help="Type of salary information provided")

    min_salary = fields.Float(
        string="Minimum Salary",
        help="Minimum salary for this position"
    )

    max_salary = fields.Float(
        string="Maximum Salary",
        help="Maximum salary for this position"
    )

    fixed_salary = fields.Float(
        string="Fixed Salary",
        help="Fixed salary amount (if salary_type is 'fixed')"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        help="Currency for salary information"
    )

    # Job Classification
    job_category_id = fields.Many2one(
        'hr.job.category',
        string="Job Category",
        help="Functional category of the job (e.g., Technology, Marketing, Design)"
    )

    job_tags = fields.Char(
        string="Job Tags",
        help="Comma-separated tags/skills for this job (e.g., React, JavaScript, Remote)"
    )

    # Job Content
    responsibilities = fields.Text(
        string="Key Responsibilities",
        help="Main responsibilities and duties for this role"
    )

    requirements = fields.Text(
        string="Requirements & Qualifications",
        help="Required skills, experience, and qualifications"
    )

    benefits = fields.Text(
        string="Benefits & Perks",
        help="Benefits, perks, and compensation package details"
    )

    # Work Arrangement
    is_remote = fields.Boolean(
        string="Remote Work",
        default=False,
        help="Indicates if this is a remote position"
    )

    # Application Management
    application_deadline = fields.Date(
        string="Application Deadline",
        help="Last date to apply for this job"
    )

    application_email = fields.Char(
        string="Application Email",
        help="Email address for job applications"
    )

    application_url = fields.Char(
        string="External Application URL",
        help="External URL for job applications"
    )

    # Company Information
    company_logo = fields.Binary(
        string="Company Logo",
        help="Company logo for job listings"
    )

    company_website = fields.Char(
        string="Company Website",
        help="Company website URL"
    )

    company_phone = fields.Char(
        string="Company Phone",
        help="Company contact phone number"
    )

    company_description = fields.Text(
        string="Company Description",
        help="Brief description of the company"
    )

    # Computed fields for job portal
    salary_display = fields.Char(
        string="Salary Display",
        compute='_compute_salary_display',
        store=True,
        help="Formatted salary display for job portal"
    )

    job_tags_list = fields.Char(
        string="Job Tags List",
        compute='_compute_job_tags_list',
        store=True,
        help="Processed job tags for frontend display"
    )

    # Computed methods
    @api.depends('salary_type', 'min_salary', 'max_salary', 'fixed_salary', 'currency_id')
    def _compute_salary_display(self):
        for job in self:
            if job.salary_type == 'fixed' and job.fixed_salary:
                job.salary_display = f"{job.currency_id.symbol}{job.fixed_salary:,.0f}"
            elif job.salary_type == 'range' and job.min_salary and job.max_salary:
                job.salary_display = f"{job.currency_id.symbol}{job.min_salary:,.0f} - {job.currency_id.symbol}{job.max_salary:,.0f}"
            elif job.salary_type == 'negotiable':
                job.salary_display = "Negotiable"
            else:
                job.salary_display = "Not specified"

    @api.depends('job_tags')
    def _compute_job_tags_list(self):
        for job in self:
            job.job_tags_list = job.job_tags or ""

    @api.model
    def get_job_portal_data(self, domain=None, limit=None, offset=0):
        """
        Get job data formatted for job portal frontend
        """
        if domain is None:
            domain = [('active', '=', True)]
        
        jobs = self.search(domain, limit=limit, offset=offset)
        
        result = []
        for job in jobs:
            try:
                # Get selection values safely
                job_type_display = job.job_type
                if hasattr(job._fields.get('job_type'), 'selection') and job._fields['job_type'].selection:
                    job_type_dict = dict(job._fields['job_type'].selection)
                    job_type_display = job_type_dict.get(job.job_type, job.job_type)
                
                experience_display = job.experience_level
                if hasattr(job._fields.get('experience_level'), 'selection') and job._fields['experience_level'].selection:
                    experience_dict = dict(job._fields['experience_level'].selection)
                    experience_display = experience_dict.get(job.experience_level, job.experience_level)
                
                education_display = job.education_level
                if hasattr(job._fields.get('education_level'), 'selection') and job._fields['education_level'].selection:
                    education_dict = dict(job._fields['education_level'].selection)
                    education_display = education_dict.get(job.education_level, job.education_level)
                
                job_data = {
                    'id': job.id,
                    'title': job.name or '',
                    'company': job.company_id.name if job.company_id else '',
                    'location': job.address_id.name if job.address_id else '',
                    'type': job_type_display,
                    'salary': job.salary_display or '',
                    'postedTime': self._get_time_ago(job.create_date),
                    'description': self._strip_html_tags(job.description or ''),
                    'tags': [tag.strip() for tag in job.job_tags.split(',')] if job.job_tags else [],
                    'isUrgent': job.is_urgent,
                    'isFeatured': job.is_featured,
                    'logo': job.company_id.name[0].upper() if job.company_id and job.company_id.name else 'C',
                    'deadline': job.application_deadline.isoformat() if job.application_deadline else None,
                    'experience': experience_display,
                    'education': education_display,
                    'responsibilities': self._strip_html_tags(job.responsibilities or ''),
                    'requirements': self._strip_html_tags(job.requirements or ''),
                    'benefits': self._strip_html_tags(job.benefits or ''),
                    'category': job.job_category_id.name if job.job_category_id else '',
                    'isRemote': job.is_remote,
                    'applicationEmail': job.application_email or '',
                    'applicationUrl': job.application_url or '',
                    'companyWebsite': job.company_website or '',
                    'companyPhone': job.company_phone or '',
                    'companyDescription': self._strip_html_tags(job.company_description or ''),
                }
                result.append(job_data)
            except Exception as e:
                # Log error and continue with next job
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Error processing job {job.id}: {str(e)}")
                continue
        
        return result

    def _strip_html_tags(self, html_text):
        """Strip HTML tags from text using Odoo's built-in helper"""
        if not html_text:
            return ''
        
        # Use Odoo's built-in HTML stripping method
        from odoo.tools import html2plaintext
        return html2plaintext(html_text).strip()

    def _get_time_ago(self, date):
        """Convert date to 'time ago' format"""
        if not date:
            return 'Unknown'
        
        try:
            from datetime import datetime, timezone
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Handle timezone-aware and timezone-naive dates
            if date.tzinfo is None:
                # If date is timezone-naive, assume it's in UTC
                date = date.replace(tzinfo=timezone.utc)
            else:
                # If date is timezone-aware, convert to UTC
                date = date.astimezone(timezone.utc)
            
            diff = now - date
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
                
        except Exception as e:
            # If there's any error with date calculation, return a fallback
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Error calculating time ago for date {date}: {str(e)}")
            return "Recently"
