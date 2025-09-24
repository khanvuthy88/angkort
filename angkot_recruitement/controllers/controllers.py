# -*- coding: utf-8 -*-

import json
from odoo import http
from odoo.http import request


class JobPortalController(http.Controller):
    
    @http.route('/api/jobs', type='http', auth='public', methods=['GET'], csrf=False)
    def get_jobs(self, **kwargs):
        """API endpoint to get jobs for the job portal"""
        try:
            # Parse query parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            category = kwargs.get('category')
            job_type = kwargs.get('type')
            location = kwargs.get('location')
            search = kwargs.get('search')
            
            # Build domain
            domain = [('active', '=', True)]
            
            if category:
                domain.append(('job_category_id.name', 'ilike', category))
            
            if job_type:
                domain.append(('job_type', '=', job_type))
                
            if location:
                domain.append(('address_id.name', 'ilike', location))
                
            if search:
                domain.append('|')
                domain.append(('name', 'ilike', search))
                domain.append(('description', 'ilike', search))
            
            # Get jobs
            jobs = request.env['hr.job'].get_job_portal_data(
                domain=domain,
                limit=limit,
                offset=offset
            )
            
            # Get total count
            total_count = request.env['hr.job'].search_count(domain)
            
            return request.make_json_response({
                'success': True,
                'data': jobs,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @http.route('/api/jobs/<int:job_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_job_detail(self, job_id, **kwargs):
        """API endpoint to get job details"""
        try:
            job = request.env['hr.job'].browse(job_id)
            
            if not job.exists() or not job.active:
                return request.make_json_response({
                    'success': False,
                    'error': 'Job not found'
                }, status=404)
            
            job_data = request.env['hr.job'].get_job_portal_data(
                domain=[('id', '=', job_id)]
            )
            
            if not job_data:
                return request.make_json_response({
                    'success': False,
                    'error': 'Job not found'
                }, status=404)
            
            return request.make_json_response({
                'success': True,
                'data': job_data[0]
            })
            
        except Exception as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @http.route('/api/categories', type='http', auth='public', methods=['GET'], csrf=False)
    def get_categories(self, **kwargs):
        """API endpoint to get job categories"""
        try:
            categories = request.env['hr.job.category'].search([
                ('active', '=', True)
            ])
            
            category_data = []
            for category in categories:
                category_data.append({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'job_count': category.active_job_count
                })
            
            return request.make_json_response({
                'success': True,
                'data': category_data
            })
            
        except Exception as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)

