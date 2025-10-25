# -*- coding: utf-8 -*-

import json
import base64
import logging
from odoo import http, fields
from odoo.http import request
from odoo.tools import config

_logger = logging.getLogger(__name__)


class JobPortalController(http.Controller):
    
    def _copy_default_user(self, user_type, name, email, password, phone=''):
        """
        Copy default user template based on user type
        
        Args:
            user_type: 'candidate' or 'employer'
            name: User's full name
            email: User's email
            password: User's password
            phone: User's phone number (optional)
        
        Returns:
            New user record or None if failed
        """
        try:
            # Get the default user template based on user type
            if user_type == 'candidate':
                default_user_xmlid = 'angkot_recruitement.default_candidate_user'
            else:
                default_user_xmlid = 'angkot_recruitement.default_employer_user'
            
            # Use SUPERUSER environment to avoid "Expected singleton" errors
            # This is necessary because auth='none' routes don't have a user in env
            env = request.env(user=request.env.ref('base.user_admin').id)
            
            # Find the default user template (must search inactive users)
            default_user = env.ref(default_user_xmlid, raise_if_not_found=False)
            
            if not default_user:
                _logger.error(f"Default user template not found: {default_user_xmlid}")
                return None
            
            _logger.info(f"Using default user template: {default_user_xmlid} (ID: {default_user.id})")
            
            # Copy the default user with new values
            # We use copy() which duplicates the user with all groups and settings
            new_user = default_user.sudo().with_context(
                no_reset_password=True,
                tracking_disable=True,
                mail_create_nolog=True,
                mail_notrack=True
            ).copy({
                'name': name,
                'login': email,
                'email': email,
                'phone': phone,
                'active': True,  # Activate the user (email verification will control access)
                'email_verified': False,  # Email not verified yet
            })
            
            # Set password after user is created
            if new_user:
                new_user.sudo().with_context(no_reset_password=True).write({'password': password})
                _logger.info(f"User created from template: ID={new_user.id}, login={new_user.login}, groups={new_user.groups_id.mapped('name')}")
            
            return new_user
            
        except Exception as e:
            _logger.error(f"Error copying default user for {user_type}: {str(e)}", exc_info=True)
            return None
    
    @http.route('/api/auth/login', type='http', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        """API endpoint for user login with session-based authentication"""
        try:
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            email = data.get('email') or data.get('username')
            password = data.get('password')
            if not email or not password:
                return request.make_json_response({
                    'success': False,
                    'error': 'Email and password are required'
                }, status=400)

            db = config['db_name']
            credential = {'login': email, 'password': password, 'type': 'password'}
            # Authenticate with Odoo
            uid = request.session.authenticate(db, credential)
            
            if not uid:
                return request.make_json_response({
                    'success': False,
                    'error': 'Invalid credentials'
                }, status=401)
            
            # Get user information - use the authenticated user from request.env.user
            user = request.env.user
            
            # Check if user has access to the job portal
            has_group1 = user.has_group('base.group_user')
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if not (has_group1 or is_admin or is_recruitment_officer):
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied. Valid account required.'
                }, status=403)
            
            # Determine user role
            if is_admin:
                role = 'admin'
            elif is_recruitment_officer:
                role = 'recruitment_officer'
            else:
                role = 'job_applicant'
            
            # Get company information
            company = user.company_id
            company_info = {
                'name': company.name if company else 'Unknown Company',
                'email': company.email if company else '',
                'phone': company.phone if company else ''
            }
            
            # Get user groups
            groups = []
            for group in user.groups_id:
                groups.append({
                    'id': group.id,
                    'name': group.name
                })
            
            # Get role-specific permissions and navigation
            permissions = self._get_role_permissions(role)
            navigation = self._get_role_navigation(role)
            
            user_profile = {
                'id': uid,
                'name': user.name,
                'email': user.email or user.login,
                'company': company_info['name'],
                'phone': company_info['phone'],
                'role': role,
                'groups': groups,
                'permissions': permissions,
                'navigation': navigation
            }
            
            return request.make_json_response({
                'success': True,
                'user': user_profile
            })
            
        except Exception as e:
            _logger.error(f"Error in login API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/auth/signup', type='http', auth='none', methods=['POST'], csrf=False)
    def signup(self, **kwargs):
        """API endpoint for user signup with proper role assignment"""
        try:
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            name = data.get('name')
            email = data.get('email')
            password = data.get('password')
            phone = data.get('phone', '')
            user_type = data.get('user_type', 'candidate')  # 'candidate' or 'employer'
            
            if not name or not email or not password:
                return request.make_json_response({
                    'success': False,
                    'error': 'Name, email, and password are required'
                }, status=400)
            
            # Check if user already exists (including inactive users)
            existing_user = request.env['res.users'].sudo().with_context(active_test=False).search([
                '|', ('login', '=', email), ('email', '=', email)
            ], limit=1)
            
            if existing_user:
                _logger.warning(f"Signup attempt for existing user: {email}, user_id: {existing_user.id}, active: {existing_user.active}")
                return request.make_json_response({
                    'success': False,
                    'error': 'An account with this email already exists. Please try logging in or use password reset.'
                }, status=400)
            
            # Determine role based on user type
            role = 'job_applicant' if user_type == 'candidate' else 'recruitment_officer'
            
            # Create user from default template
            _logger.info(f"Creating {user_type} user for {email} using default template")
            
            try:
                # Copy default user template
                new_user = self._copy_default_user(user_type, name, email, password, phone)
                
                # Validate user creation
                if not new_user or not new_user.exists():
                    _logger.error(f"User creation from template returned empty recordset for email: {email}")
                    return request.make_json_response({
                        'success': False,
                        'error': 'Failed to create user account. Please try again.'
                    }, status=500)
                
                _logger.info(f"User created successfully from template: ID={new_user.id}, login={new_user.login}, active={new_user.active}, groups={new_user.groups_id.mapped('name')}")
                
            except Exception as create_error:
                _logger.error(f"Exception during user creation for {email}: {str(create_error)}", exc_info=True)
                return request.make_json_response({
                    'success': False,
                    'error': f'Failed to create user account: {str(create_error)}'
                }, status=500)
            
            # Create candidate profile if user is a candidate
            if user_type == 'candidate':
                try:
                    candidate_vals = {
                        'partner_name': name,
                        'email_from': email,
                        'partner_phone': phone or '',
                        'user_id': new_user.id,
                        'company_id': 1,  # Default company
                    }
                    _logger.info(f"Creating candidate profile for user {new_user.id} with values: {candidate_vals}")
                    candidate = request.env['hr.candidate'].sudo().create(candidate_vals)
                    
                    # Validate candidate creation
                    if not candidate or not candidate.exists():
                        _logger.error(f"Candidate creation returned empty recordset for user {new_user.id}")
                        # Don't fail the signup, but log the error
                    else:
                        # Link candidate profile to user
                        new_user.sudo().write({'candidate_id': candidate.id})
                        _logger.info(f"Successfully created and linked candidate profile {candidate.id} to user {new_user.id}")
                except Exception as candidate_error:
                    _logger.error(f"Exception creating candidate profile for user {new_user.id}: {str(candidate_error)}")
                    # Don't fail the signup, candidate profile can be created later
            
            # Send verification email
            # Get base URL from request
            base_url = request.httprequest.host_url.rstrip('/')
            # For development, use the Next.js URL
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                base_url = 'http://localhost:3001'
            
            try:
                _logger.info(f"Attempting to send verification email to {email} for user {new_user.id}")
                new_user.send_verification_email(base_url)
                _logger.info(f"Verification email sent successfully to {email}")
            except Exception as e:
                _logger.error(f"Failed to send verification email to {email}: {str(e)}", exc_info=True)
                # Don't fail the registration if email sending fails
            
            # Get company information
            company = new_user.company_id
            company_info = {
                'name': company.name if company else 'Unknown Company',
                'email': company.email if company else '',
                'phone': company.phone if company else ''
            }
            
            # Get user groups
            groups = []
            for group in new_user.groups_id:
                groups.append({
                    'id': group.id,
                    'name': group.name
                })
            
            # Get role-specific permissions and navigation
            permissions = self._get_role_permissions(role)
            navigation = self._get_role_navigation(role)
            
            user_profile = {
                'id': new_user.id,
                'name': new_user.name,
                'email': new_user.email or new_user.login,
                'company': company_info['name'],
                'phone': company_info['phone'],
                'role': role,
                'groups': groups,
                'permissions': permissions,
                'navigation': navigation
            }
            
            return request.make_json_response({
                'success': True,
                'user': user_profile,
                'message': f'{user_type.title()} account created successfully',
                'email_verification_required': True,
                'email_sent': True
            })
            
        except Exception as e:
            _logger.error(f"Error in signup API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Failed to create account. Please try again.'
            }, status=500)

    @http.route('/api/auth/verify-email', type='http', auth='none', methods=['POST'], csrf=False)
    def verify_email(self, **kwargs):
        """API endpoint for email verification"""
        try:
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            token = data.get('token')
            email = data.get('email')
            
            if not token or not email:
                return request.make_json_response({
                    'success': False,
                    'error': 'Token and email are required'
                }, status=400)
            
            # Verify the email with token
            verified = request.env['res.users'].verify_email_by_token(token, email)
            
            if verified:
                # Get user info
                user = request.env['res.users'].sudo().search([('email', '=', email)], limit=1)
                
                return request.make_json_response({
                    'success': True,
                    'message': 'Email verified successfully. You can now log in.',
                    'user': {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email,
                        'verified': True
                    }
                })
            else:
                return request.make_json_response({
                    'success': False,
                    'error': 'Invalid or expired verification token'
                }, status=400)
            
        except Exception as e:
            _logger.error(f"Error in verify_email API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)

    @http.route('/api/auth/resend-verification', type='http', auth='none', methods=['POST'], csrf=False)
    def resend_verification(self, **kwargs):
        """API endpoint to resend verification email"""
        try:
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            email = data.get('email')
            
            if not email:
                return request.make_json_response({
                    'success': False,
                    'error': 'Email is required'
                }, status=400)
            
            # Find user
            user = request.env['res.users'].sudo().search([
                ('email', '=', email),
                ('email_verified', '=', False)
            ], limit=1)
            
            if not user:
                return request.make_json_response({
                    'success': False,
                    'error': 'User not found or already verified'
                }, status=404)
            
            # Send verification email
            base_url = request.httprequest.host_url.rstrip('/')
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                base_url = 'http://localhost:3001'
            
            user.send_verification_email(base_url)
            
            return request.make_json_response({
                'success': True,
                'message': 'Verification email sent successfully'
            })
            
        except Exception as e:
            _logger.error(f"Error in resend_verification API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)

    @http.route('/api/auth/me', type='http', auth='user', methods=['GET'], csrf=False)
    def get_user_info(self, **kwargs):
        """API endpoint to get current user information"""
        try:
            user = request.env.user
            
            # Determine user role
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if is_admin:
                role = 'admin'
            elif is_recruitment_officer:
                role = 'recruitment_officer'
            else:
                role = 'job_applicant'
            
            # Get company information
            company = user.company_id
            company_info = {
                'name': company.name if company else 'Unknown Company',
                'email': company.email if company else '',
                'phone': company.phone if company else ''
            }
            
            # Get user groups
            groups = []
            for group in user.groups_id:
                groups.append({
                    'id': group.id,
                    'name': group.name
                })
            
            # Get role-specific permissions and navigation
            permissions = self._get_role_permissions(role)
            navigation = self._get_role_navigation(role)
            
            user_profile = {
                'id': user.id,
                'name': user.name,
                'email': user.email or user.login,
                'company': company_info['name'],
                'phone': company_info['phone'],
                'role': role,
                'groups': groups,
                'permissions': permissions,
                'navigation': navigation
            }
            
            return request.make_json_response({
                'success': True,
                'user': user_profile
            })
            
        except Exception as e:
            _logger.error(f"Error in get_user_info API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/auth/logout', type='http', auth='user', methods=['POST'], csrf=False)
    def logout(self, **kwargs):
        """API endpoint for user logout"""
        try:
            # Destroy the session
            request.session.logout(keep_db=True)
            
            return request.make_json_response({
                'success': True,
                'message': 'Logged out successfully'
            })
            
        except Exception as e:
            _logger.error(f"Error in logout API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    def _get_role_permissions(self, role: str):
        """Get role-specific permissions"""
        permissions_map = {
            'admin': [
                'read_all_jobs', 'write_all_jobs', 'delete_all_jobs',
                'read_all_applications', 'write_all_applications', 'delete_all_applications',
                'manage_users', 'manage_settings', 'view_analytics'
            ],
            'recruitment_officer': [
                'read_my_jobs', 'write_my_jobs', 'delete_my_jobs',
                'read_my_applications', 'write_my_applications',
                'manage_candidates', 'view_my_analytics'
            ],
            'job_applicant': [
                'read_public_jobs', 'apply_jobs', 'read_my_applications',
                'update_profile', 'view_my_activity'
            ]
        }
        return permissions_map.get(role, permissions_map['job_applicant'])
    
    def _get_role_navigation(self, role: str):
        """Get role-specific navigation items"""
        navigation_map = {
            'admin': [
                {'name': 'Dashboard', 'href': '/dashboard', 'icon': 'LayoutDashboard'},
                {'name': 'All Jobs', 'href': '/dashboard/jobs', 'icon': 'Briefcase'},
                {'name': 'All Applications', 'href': '/dashboard/applications', 'icon': 'Users'},
                {'name': 'Users', 'href': '/dashboard/users', 'icon': 'UserCheck'},
                {'name': 'Settings', 'href': '/dashboard/settings', 'icon': 'Settings'}
            ],
            'recruitment_officer': [
                {'name': 'Dashboard', 'href': '/dashboard', 'icon': 'LayoutDashboard'},
                {'name': 'My Jobs', 'href': '/dashboard/jobs', 'icon': 'Briefcase'},
                {'name': 'Applications', 'href': '/dashboard/applications', 'icon': 'Users'},
                {'name': 'Messages', 'href': '/dashboard/messages', 'icon': 'MessageSquare'},
                {'name': 'Profile', 'href': '/dashboard/profile', 'icon': 'User'}
            ],
            'job_applicant': [
                {'name': 'Dashboard', 'href': '/dashboard', 'icon': 'LayoutDashboard'},
                {'name': 'Browse Jobs', 'href': '/jobs', 'icon': 'Search'},
                {'name': 'My Applications', 'href': '/dashboard/applications', 'icon': 'Send'},
                {'name': 'Messages', 'href': '/dashboard/messages', 'icon': 'MessageSquare'},
                {'name': 'Profile', 'href': '/dashboard/profile', 'icon': 'User'}
            ]
        }
        return navigation_map.get(role, navigation_map['job_applicant'])
    
    @http.route('/api/activities', type='http', auth='user', methods=['GET'], csrf=False)
    def get_activities(self, **kwargs):
        """API endpoint to get user activities"""
        try:
            user = request.env.user
            
            # Get activities from mail.activity model
            activities = request.env['mail.activity'].sudo().search([
                ('user_id', '=', user.id)
            ], limit=50, order='date_deadline asc')
            
            activity_data = []
            for activity in activities:
                activity_data.append({
                    'id': activity.id,
                    'summary': activity.summary or '',
                    'note': activity.note or '',
                    'date_deadline': activity.date_deadline.isoformat() if activity.date_deadline else None,
                    'date_create': activity.create_date.isoformat(),
                    'activity_type_id': activity.activity_type_id.id if activity.activity_type_id else None,
                    'activity_type_name': activity.activity_type_id.name if activity.activity_type_id else '',
                    'res_model': activity.res_model,
                    'res_id': activity.res_id,
                    'res_name': activity.res_name or '',
                    'state': activity.state,
                    'user_id': activity.user_id.id,
                    'user_name': activity.user_id.name,
                    'create_uid': activity.create_uid.id,
                    'create_uid_name': activity.create_uid.name
                })
            
            return request.make_json_response({
                'success': True,
                'data': activity_data,
                'total': len(activity_data)
            })
            
        except Exception as e:
            _logger.error(f"Error in get_activities API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/activities/<int:activity_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_activity_detail(self, activity_id, **kwargs):
        """API endpoint to get activity details"""
        try:
            user = request.env.user
            
            # Get the activity
            activity = request.env['mail.activity'].sudo().browse(activity_id)
            
            if not activity.exists():
                return request.make_json_response({
                    'success': False,
                    'error': 'Activity not found'
                }, status=404)
            
            # Check if user has access to this activity
            if activity.user_id.id != user.id and not user.has_group('base.group_system'):
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            # Get related record details if available
            related_record = None
            if activity.res_model and activity.res_id:
                try:
                    model = request.env[activity.res_model].sudo().browse(activity.res_id)
                    if model.exists():
                        related_record = {
                            'model': activity.res_model,
                            'id': activity.res_id,
                            'name': model.display_name if hasattr(model, 'display_name') else str(model.name) if hasattr(model, 'name') else f"{activity.res_model}_{activity.res_id}"
                        }
                except Exception as e:
                    _logger.warning(f"Could not get related record for {activity.res_model}:{activity.res_id}: {e}")
            
            activity_data = {
                'id': activity.id,
                'summary': activity.summary or '',
                'note': activity.note or '',
                'date_deadline': activity.date_deadline.isoformat() if activity.date_deadline else None,
                'date_create': activity.create_date.isoformat(),
                'activity_type_id': activity.activity_type_id.id if activity.activity_type_id else None,
                'activity_type_name': activity.activity_type_id.name if activity.activity_type_id else '',
                'res_model': activity.res_model,
                'res_id': activity.res_id,
                'res_name': activity.res_name or '',
                'state': activity.state,
                'user_id': activity.user_id.id,
                'user_name': activity.user_id.name,
                'create_uid': activity.create_uid.id,
                'create_uid_name': activity.create_uid.name,
                'related_record': related_record
            }
            
            return request.make_json_response({
                'success': True,
                'data': activity_data
            })
            
        except Exception as e:
            _logger.error(f"Error in get_activity_detail API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/candidates', type='http', auth='user', methods=['GET'], csrf=False)
    def get_candidates(self, **kwargs):
        """API endpoint to get job candidates/applicants"""
        try:
            user = request.env.user
            
            # Parse query parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            job_id = kwargs.get('job_id')
            status = kwargs.get('status')
            search = kwargs.get('search')
            
            # Build domain
            domain = []
            
            # Check user role and apply appropriate filters
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if not is_admin and not is_recruitment_officer:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Insufficient permissions'
                }, status=403)
            
            # Apply filters
            if job_id:
                domain.append(('job_id', '=', int(job_id)))
            
            if status:
                if status == 'new':
                    domain.append(('stage_id.name', 'ilike', 'new'))
                elif status == 'qualified':
                    domain.append(('stage_id.name', 'ilike', 'qualified'))
                elif status == 'interview':
                    domain.append(('stage_id.name', 'ilike', 'interview'))
                elif status == 'offer':
                    domain.append(('stage_id.name', 'ilike', 'offer'))
                elif status == 'hired':
                    domain.append(('stage_id.name', 'ilike', 'hired'))
                elif status == 'rejected':
                    domain.append(('stage_id.name', 'ilike', 'rejected'))
            
            if search:
                domain.append('|')
                domain.append(('partner_name', 'ilike', search))
                domain.append(('email_from', 'ilike', search))
            
            # Get applicants
            applicants = request.env['hr.applicant'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='create_date desc'
            )
            
            # Get total count
            total_count = request.env['hr.applicant'].sudo().search_count(domain)
            
            # Format applicant data
            candidate_data = []
            for applicant in applicants:
                candidate_data.append({
                    'id': applicant.id,
                    'name': applicant.partner_name or '',
                    'email': applicant.email_from or '',
                    'phone': applicant.partner_phone or '',
                    'job_id': applicant.job_id.id if applicant.job_id else None,
                    'job_title': applicant.job_id.name if applicant.job_id else '',
                    'stage_id': applicant.stage_id.id if applicant.stage_id else None,
                    'stage_name': applicant.stage_id.name if applicant.stage_id else '',
                    'application_source': applicant.application_source,
                    'create_date': applicant.create_date.isoformat(),
                    'write_date': applicant.write_date.isoformat() if applicant.write_date else applicant.create_date.isoformat(),
                    'linkedin_url': applicant.linkedin_url or '',
                    'portfolio_url': applicant.portfolio_url or '',
                    'resume_filename': applicant.resume_filename or '',
                    'cover_letter': applicant.cover_letter or '',
                    'availability': applicant.availability or '',
                    'expected_salary': applicant.expected_salary or 0,
                    'salary_proposed': applicant.salary_proposed or 0,
                    'salary_expected': applicant.salary_expected or 0,
                    'salary_proposed_extra': applicant.salary_proposed_extra or '',
                    'availability_date': applicant.availability_date.isoformat() if applicant.availability_date else None,
                    'user_id': applicant.user_id.id if applicant.user_id else None,
                    'user_name': applicant.user_id.name if applicant.user_id else '',
                    'company_id': applicant.company_id.id if applicant.company_id else None,
                    'company_name': applicant.company_id.name if applicant.company_id else '',
                    'department_id': applicant.department_id.id if applicant.department_id else None,
                    'department_name': applicant.department_id.name if applicant.department_id else '',
                    'priority': applicant.priority,
                    'ref': applicant.ref or '',
                    'active': applicant.active
                })
            
            return request.make_json_response({
                'success': True,
                'data': candidate_data,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            _logger.error(f"Error in get_candidates API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/candidates/<int:candidate_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_candidate_detail(self, candidate_id, **kwargs):
        """API endpoint to get candidate details"""
        try:
            user = request.env.user
            
            # Get the applicant
            applicant = request.env['hr.applicant'].sudo().browse(candidate_id)
            
            if not applicant.exists():
                return request.make_json_response({
                    'success': False,
                    'error': 'Candidate not found'
                }, status=404)
            
            # Check user permissions
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if not is_admin and not is_recruitment_officer:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Insufficient permissions'
                }, status=403)
            
            # Get candidate details
            candidate_data = {
                'id': applicant.id,
                'name': applicant.partner_name or '',
                'email': applicant.email_from or '',
                'phone': applicant.partner_phone or '',
                'job_id': applicant.job_id.id if applicant.job_id else None,
                'job_title': applicant.job_id.name if applicant.job_id else '',
                'stage_id': applicant.stage_id.id if applicant.stage_id else None,
                'stage_name': applicant.stage_id.name if applicant.stage_id else '',
                'application_source': applicant.application_source,
                'create_date': applicant.create_date.isoformat(),
                'write_date': applicant.write_date.isoformat() if applicant.write_date else applicant.create_date.isoformat(),
                'linkedin_url': applicant.linkedin_url or '',
                'portfolio_url': applicant.portfolio_url or '',
                'resume_filename': applicant.resume_filename or '',
                'cover_letter': applicant.cover_letter or '',
                'availability': applicant.availability or '',
                'expected_salary': applicant.expected_salary or 0,
                'salary_proposed': applicant.salary_proposed or 0,
                'salary_expected': applicant.salary_expected or 0,
                'salary_proposed_extra': applicant.salary_proposed_extra or '',
                'availability_date': applicant.availability_date.isoformat() if applicant.availability_date else None,
                'user_id': applicant.user_id.id if applicant.user_id else None,
                'user_name': applicant.user_id.name if applicant.user_id else '',
                'company_id': applicant.company_id.id if applicant.company_id else None,
                'company_name': applicant.company_id.name if applicant.company_id else '',
                'department_id': applicant.department_id.id if applicant.department_id else None,
                'department_name': applicant.department_id.name if applicant.department_id else '',
                'priority': applicant.priority,
                'ref': applicant.ref or '',
                'active': applicant.active,
                'description': applicant.description or '',
                'partner_id': applicant.partner_id.id if applicant.partner_id else None,
                'partner_name': applicant.partner_id.name if applicant.partner_id else '',
                'partner_phone': applicant.partner_phone or '',
                'partner_mobile': applicant.partner_mobile or '',
                'partner_email': applicant.partner_email or '',
                'partner_zip': applicant.partner_zip or '',
                'partner_city': applicant.partner_city or '',
                'partner_country_id': applicant.partner_country_id.id if applicant.partner_country_id else None,
                'partner_country_name': applicant.partner_country_id.name if applicant.partner_country_id else '',
                'partner_state_id': applicant.partner_state_id.id if applicant.partner_state_id else None,
                'partner_state_name': applicant.partner_state_id.name if applicant.partner_state_id else '',
                'partner_street': applicant.partner_street or '',
                'partner_street2': applicant.partner_street2 or '',
                'partner_function': applicant.partner_function or '',
                'partner_title': applicant.partner_title.id if applicant.partner_title else None,
                'partner_title_name': applicant.partner_title.name if applicant.partner_title else '',
                'partner_lang': applicant.partner_lang or '',
                'partner_gender': applicant.partner_gender or '',
                'partner_marital': applicant.partner_marital or '',
                'partner_children': applicant.partner_children or 0,
                'partner_birthday': applicant.partner_birthday.isoformat() if applicant.partner_birthday else None,
                'partner_is_blacklisted': applicant.partner_is_blacklisted,
                'partner_employee': applicant.partner_employee,
                'partner_employee_ids': [emp.id for emp in applicant.partner_employee_ids] if applicant.partner_employee_ids else [],
                'partner_employee_names': [emp.name for emp in applicant.partner_employee_ids] if applicant.partner_employee_ids else [],
                'partner_employee_count': len(applicant.partner_employee_ids) if applicant.partner_employee_ids else 0,
                'partner_employee_active_count': len(applicant.partner_employee_ids.filtered('active')) if applicant.partner_employee_ids else 0,
                'partner_employee_inactive_count': len(applicant.partner_employee_ids.filtered(lambda x: not x.active)) if applicant.partner_employee_ids else 0,
                'partner_employee_active_ids': [emp.id for emp in applicant.partner_employee_ids.filtered('active')] if applicant.partner_employee_ids else [],
                'partner_employee_inactive_ids': [emp.id for emp in applicant.partner_employee_ids.filtered(lambda x: not x.active)] if applicant.partner_employee_ids else [],
                'partner_employee_active_names': [emp.name for emp in applicant.partner_employee_ids.filtered('active')] if applicant.partner_employee_ids else [],
                'partner_employee_inactive_names': [emp.name for emp in applicant.partner_employee_ids.filtered(lambda x: not x.active)] if applicant.partner_employee_ids else []
            }
            
            return request.make_json_response({
                'success': True,
                'data': candidate_data
            })
            
        except Exception as e:
            _logger.error(f"Error in get_candidate_detail API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/employer/jobs', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employer_jobs(self, **kwargs):
        """API endpoint to get jobs for employer dashboard"""
        try:
            user = request.env.user
            
            # Parse query parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            status = kwargs.get('status')
            search = kwargs.get('search')
            
            # Check user permissions
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if not is_admin and not is_recruitment_officer:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Insufficient permissions'
                }, status=403)
            
            # Build domain
            domain = []
            if not is_admin:
                # Non-admin users can only see their own jobs
                domain.append(('user_id', '=', user.id))
            
            if status:
                if status == 'draft':
                    domain.append(('state', '=', 'draft'))
                elif status == 'open':
                    domain.append(('state', '=', 'open'))
                elif status == 'recruit':
                    domain.append(('state', '=', 'recruit'))
                elif status == 'done':
                    domain.append(('state', '=', 'done'))
                elif status == 'cancel':
                    domain.append(('state', '=', 'cancel'))
            
            if search:
                domain.append('|')
                domain.append(('name', 'ilike', search))
                domain.append(('description', 'ilike', search))
            
            # Get jobs
            jobs = request.env['hr.job'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='create_date desc'
            )
            
            # Get total count
            total_count = request.env['hr.job'].sudo().search_count(domain)
            
            # Format job data
            job_data = []
            for job in jobs:
                job_data.append({
                    'id': job.id,
                    'name': job.name,
                    'description': job.description or '',
                    'state': job.state,
                    'no_of_recruitment': job.no_of_recruitment,
                    'no_of_hired_employee': job.no_of_hired_employee,
                    'no_of_employee': job.no_of_employee,
                    'expected_employees': job.expected_employees,
                    'create_date': job.create_date.isoformat(),
                    'write_date': job.write_date.isoformat() if job.write_date else job.create_date.isoformat(),
                    'user_id': job.user_id.id if job.user_id else None,
                    'user_name': job.user_id.name if job.user_id else '',
                    'department_id': job.department_id.id if job.department_id else None,
                    'department_name': job.department_id.name if job.department_id else '',
                    'company_id': job.company_id.id if job.company_id else None,
                    'company_name': job.company_id.name if job.company_id else '',
                    'address_id': job.address_id.id if job.address_id else None,
                    'address_name': job.address_id.name if job.address_id else '',
                    'job_type': job.job_type,
                    'is_featured': job.is_featured,
                    'is_urgent': job.is_urgent,
                    'is_remote': job.is_remote,
                    'active': job.active,
                    'application_count': job.application_count,
                    'application_ids': [app.id for app in job.application_ids] if job.application_ids else [],
                    'application_names': [app.partner_name for app in job.application_ids] if job.application_ids else []
                })
            
            return request.make_json_response({
                'success': True,
                'data': job_data,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            _logger.error(f"Error in get_employer_jobs API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/employer/applications', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employer_applications(self, **kwargs):
        """API endpoint to get applications for employer dashboard"""
        try:
            user = request.env.user
            
            # Parse query parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            job_id = kwargs.get('job_id')
            status = kwargs.get('status')
            search = kwargs.get('search')
            
            # Check user permissions
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if not is_admin and not is_recruitment_officer:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Insufficient permissions'
                }, status=403)
            
            # Build domain
            domain = []
            if not is_admin:
                # Non-admin users can only see applications for their jobs
                user_jobs = request.env['hr.job'].sudo().search([('user_id', '=', user.id)])
                if user_jobs:
                    domain.append(('job_id', 'in', user_jobs.ids))
                else:
                    # No jobs, return empty result
                    return request.make_json_response({
                        'success': True,
                        'data': [],
                        'total': 0,
                        'limit': limit,
                        'offset': offset
                    })
            
            if job_id:
                domain.append(('job_id', '=', int(job_id)))
            
            if status:
                if status == 'new':
                    domain.append(('stage_id.name', 'ilike', 'new'))
                elif status == 'qualified':
                    domain.append(('stage_id.name', 'ilike', 'qualified'))
                elif status == 'interview':
                    domain.append(('stage_id.name', 'ilike', 'interview'))
                elif status == 'offer':
                    domain.append(('stage_id.name', 'ilike', 'offer'))
                elif status == 'hired':
                    domain.append(('stage_id.name', 'ilike', 'hired'))
                elif status == 'rejected':
                    domain.append(('stage_id.name', 'ilike', 'rejected'))
            
            if search:
                domain.append('|')
                domain.append(('partner_name', 'ilike', search))
                domain.append(('email_from', 'ilike', search))
            
            # Get applications
            applications = request.env['hr.applicant'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='create_date desc'
            )
            
            # Get total count
            total_count = request.env['hr.applicant'].sudo().search_count(domain)
            
            # Format application data
            application_data = []
            for application in applications:
                application_data.append({
                    'id': application.id,
                    'name': application.partner_name or '',
                    'email': application.email_from or '',
                    'phone': application.partner_phone or '',
                    'job_id': application.job_id.id if application.job_id else None,
                    'job_title': application.job_id.name if application.job_id else '',
                    'stage_id': application.stage_id.id if application.stage_id else None,
                    'stage_name': application.stage_id.name if application.stage_id else '',
                    'application_source': application.application_source,
                    'create_date': application.create_date.isoformat(),
                    'write_date': application.write_date.isoformat() if application.write_date else application.create_date.isoformat(),
                    'linkedin_url': application.linkedin_url or '',
                    'portfolio_url': application.portfolio_url or '',
                    'resume_filename': application.resume_filename or '',
                    'cover_letter': application.cover_letter or '',
                    'priority': application.priority,
                    'ref': application.ref or '',
                    'active': application.active
                })
            
            return request.make_json_response({
                'success': True,
                'data': application_data,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            _logger.error(f"Error in get_employer_applications API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/employer/stats', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employer_stats(self, **kwargs):
        """API endpoint to get employer statistics"""
        try:
            user = request.env.user
            
            # Check user permissions
            is_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_recruitment_officer = user.has_group('angkot_recruitement.group_hr_recruitment_employer')
            
            if not is_admin and not is_recruitment_officer:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Insufficient permissions'
                }, status=403)
            
            # Build domain for user's jobs
            job_domain = []
            if not is_admin:
                job_domain.append(('user_id', '=', user.id))
            
            # Get user's jobs
            user_jobs = request.env['hr.job'].sudo().search(job_domain)
            job_ids = user_jobs.ids if user_jobs else []
            
            # Get statistics
            total_jobs = len(user_jobs) if user_jobs else 0
            active_jobs = len(user_jobs.filtered('active')) if user_jobs else 0
            draft_jobs = len(user_jobs.filtered(lambda x: x.state == 'draft')) if user_jobs else 0
            open_jobs = len(user_jobs.filtered(lambda x: x.state == 'open')) if user_jobs else 0
            recruit_jobs = len(user_jobs.filtered(lambda x: x.state == 'recruit')) if user_jobs else 0
            done_jobs = len(user_jobs.filtered(lambda x: x.state == 'done')) if user_jobs else 0
            
            # Get application statistics
            application_domain = []
            if job_ids:
                application_domain.append(('job_id', 'in', job_ids))
            else:
                # No jobs, return empty stats
                return request.make_json_response({
                    'success': True,
                    'data': {
                        'jobs': {
                            'total': 0,
                            'active': 0,
                            'draft': 0,
                            'open': 0,
                            'recruit': 0,
                            'done': 0
                        },
                        'applications': {
                            'total': 0,
                            'new': 0,
                            'qualified': 0,
                            'interview': 0,
                            'offer': 0,
                            'hired': 0,
                            'rejected': 0
                        }
                    }
                })
            
            applications = request.env['hr.applicant'].sudo().search(application_domain)
            total_applications = len(applications) if applications else 0
            
            # Count applications by stage
            new_applications = len(applications.filtered(lambda x: x.stage_id and 'new' in x.stage_id.name.lower())) if applications else 0
            qualified_applications = len(applications.filtered(lambda x: x.stage_id and 'qualified' in x.stage_id.name.lower())) if applications else 0
            interview_applications = len(applications.filtered(lambda x: x.stage_id and 'interview' in x.stage_id.name.lower())) if applications else 0
            offer_applications = len(applications.filtered(lambda x: x.stage_id and 'offer' in x.stage_id.name.lower())) if applications else 0
            hired_applications = len(applications.filtered(lambda x: x.stage_id and 'hired' in x.stage_id.name.lower())) if applications else 0
            rejected_applications = len(applications.filtered(lambda x: x.stage_id and 'rejected' in x.stage_id.name.lower())) if applications else 0
            
            stats_data = {
                'jobs': {
                    'total': total_jobs,
                    'active': active_jobs,
                    'draft': draft_jobs,
                    'open': open_jobs,
                    'recruit': recruit_jobs,
                    'done': done_jobs
                },
                'applications': {
                    'total': total_applications,
                    'new': new_applications,
                    'qualified': qualified_applications,
                    'interview': interview_applications,
                    'offer': offer_applications,
                    'hired': hired_applications,
                    'rejected': rejected_applications
                }
            }
            
            return request.make_json_response({
                'success': True,
                'data': stats_data
            })
            
        except Exception as e:
            _logger.error(f"Error in get_employer_stats API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/contact', type='http', auth='none', methods=['POST'], csrf=False)
    def submit_contact_form(self, **kwargs):
        """API endpoint to submit contact form"""
        try:
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            # Validate required fields
            required_fields = ['name', 'email', 'subject', 'message']
            for field in required_fields:
                if not data.get(field):
                    return request.make_json_response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Create a mail.message record for the contact form
            mail_data = {
                'subject': f"Contact Form: {data.get('subject')}",
                'body': f"""
Contact Form Submission:

Name: {data.get('name')}
Email: {data.get('email')}
Phone: {data.get('phone', 'Not provided')}
Company: {data.get('company', 'Not provided')}
Subject: {data.get('subject')}

Message:
{data.get('message')}

Submitted at: {fields.Datetime.now()}
                """.strip(),
                'email_from': data.get('email'),
                'email_to': 'admin@example.com',  # Configure this as needed
                'message_type': 'email',
                'subtype_id': request.env['mail.message.subtype'].sudo().search([('name', '=', 'Discussions')], limit=1).id,
                'author_id': request.env['res.partner'].sudo().search([('email', '=', data.get('email'))], limit=1).id or False,
                'model': 'mail.thread',
                'res_id': 0,
                'state': 'sent'
            }
            
            # Create the mail message
            mail_message = request.env['mail.message'].sudo().create(mail_data)
            
            # Also create a crm.lead for tracking
            lead_data = {
                'name': f"Contact: {data.get('subject')}",
                'partner_name': data.get('name'),
                'email_from': data.get('email'),
                'phone': data.get('phone', ''),
                'description': data.get('message'),
                'type': 'lead',
                'source_id': request.env['utm.source'].sudo().search([('name', '=', 'Website Contact Form')], limit=1).id or False,
                'medium_id': request.env['utm.medium'].sudo().search([('name', '=', 'Website')], limit=1).id or False,
                'campaign_id': request.env['utm.campaign'].sudo().search([('name', '=', 'Contact Form')], limit=1).id or False,
                'user_id': request.env['res.users'].sudo().search([('groups_id', 'in', request.env.ref('base.group_system').id)], limit=1).id or False,
                'team_id': request.env['crm.team'].sudo().search([('name', '=', 'Website')], limit=1).id or False,
                'tag_ids': [(6, 0, request.env['crm.tag'].sudo().search([('name', '=', 'Contact Form')], limit=1).ids)] if request.env['crm.tag'].sudo().search([('name', '=', 'Contact Form')], limit=1) else False
            }
            
            lead = request.env['crm.lead'].sudo().create(lead_data)
            
            return request.make_json_response({
                'success': True,
                'message': 'Contact form submitted successfully',
                'data': {
                    'mail_message_id': mail_message.id,
                    'lead_id': lead.id,
                    'reference': lead.name
                }
            })
            
        except Exception as e:
            _logger.error(f"Error in submit_contact_form API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
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
            featured = kwargs.get('featured')
            urgent = kwargs.get('urgent')
            remote = kwargs.get('remote')
            
            # Build domain
            domain = [('active', '=', True)]
            
            if category:
                # Try to find category by name first, then by ID
                category_obj = request.env['hr.job.category'].sudo().search([('name', 'ilike', category)], limit=1)
                if category_obj:
                    domain.append(('job_category_id', '=', category_obj.id))
                else:
                    # If no category found, return empty result
                    return request.make_json_response({
                        'success': True,
                        'data': [],
                        'total': 0,
                        'limit': limit,
                        'offset': offset
                    })
            
            if job_type:
                domain.append(('job_type', '=', job_type))
                
            if location:
                domain.append(('address_id.name', 'ilike', location))
                
            if search:
                domain.append('|')
                domain.append(('name', 'ilike', search))
                domain.append(('description', 'ilike', search))
            
            if featured:
                domain.append(('is_featured', '=', True))
            
            if urgent:
                domain.append(('is_urgent', '=', True))
            
            if remote:
                domain.append(('is_remote', '=', True))
            
            # Get jobs using sudo to bypass access rights for public API
            jobs = request.env['hr.job'].sudo().get_job_portal_data(
                domain=domain,
                limit=limit,
                offset=offset
            )
            
            # Get total count
            total_count = request.env['hr.job'].sudo().search_count(domain)
            
            return request.make_json_response({
                'success': True,
                'data': jobs,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in get_jobs API: {str(e)}")
            _logger.error(f"Parameters: {kwargs}")
            return request.make_json_response({
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0,
                'limit': 20,
                'offset': 0
            }, status=500)
    
    @http.route('/api/jobs/<int:job_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_job_detail(self, job_id, **kwargs):
        """API endpoint to get job details"""
        try:
            job = request.env['hr.job'].sudo().browse(job_id)
            
            if not job.exists() or not job.active:
                return request.make_json_response({
                    'success': False,
                    'error': 'Job not found'
                }, status=404)
            
            job_data = request.env['hr.job'].sudo().get_job_portal_data(
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
            # Parse query parameters
            limit = int(kwargs.get('limit', 50))
            offset = int(kwargs.get('offset', 0))
            search = kwargs.get('search', '')
            
            # Build domain
            domain = [('active', '=', True)]
            if search:
                domain.append(('name', 'ilike', search))
            
            # Get categories using sudo to bypass access rights for public API
            categories = request.env['hr.job.category'].sudo().search(
                domain, 
                limit=limit, 
                offset=offset,
                order='sequence, name'
            )
            
            # Get total count
            total_count = request.env['hr.job.category'].sudo().search_count(domain)
            
            category_data = []
            for category in categories:
                category_data.append({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description or '',
                    'job_count': category.active_job_count,
                    'total_job_count': category.job_count,
                    'sequence': category.sequence,
                    'active': category.active
                })
            
            return request.make_json_response({
                'success': True,
                'data': category_data,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @http.route('/api/jobs/<int:job_id>/apply', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_job_application(self, job_id, **kwargs):
        """API endpoint to submit a job application using existing hr.applicant model"""
        try:
            # Get the job
            job = request.env['hr.job'].sudo().browse(job_id)
            
            if not job.exists() or not job.active:
                return request.make_json_response({
                    'success': False,
                    'error': 'Job not found'
                }, status=404)
            
            # Get form data from request
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            # Validate required fields
            required_fields = ['applicant_name', 'email']
            for field in required_fields:
                if not data.get(field):
                    return request.make_json_response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Prepare application data for existing hr.applicant model
            application_data = {
                'applicant_name': data.get('applicant_name'),
                'email': data.get('email'),
                'phone': data.get('phone', ''),
                'linkedin_url': data.get('linkedin_url', ''),
                'portfolio_url': data.get('portfolio_url', ''),
            }
            
            # Handle file upload if present
            if 'resume_file' in data and data['resume_file']:
                try:
                    # Keep base64 data for attachment creation
                    application_data['resume_file'] = data['resume_file']
                    application_data['resume_filename'] = data.get('resume_filename', 'resume.pdf')
                except Exception as e:
                    _logger.warning(f"Error processing resume file: {e}")
            
            # Create the application using existing hr.applicant model
            application = request.env['hr.applicant'].sudo().create_from_job_portal(job_id, application_data)
            
            return request.make_json_response({
                'success': True,
                'message': 'Application submitted successfully',
                'application_id': application.id,
                'data': {
                    'id': application.id,
                    'applicant_name': application.partner_name,
                    'email': application.email_from,
                    'application_date': application.create_date.isoformat(),
                    'status': application.stage_id.name if application.stage_id else 'New',
                    'source': dict(application._fields['application_source'].selection)[application.application_source]
                }
            })
            
        except Exception as e:
            _logger.error(f"Error in submit_job_application API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @http.route('/api/invoices', type='http', auth='angkit', methods=['GET'], csrf=False)
    def get_invoices(self, **kwargs):
        """API endpoint to get invoices with role-based access control"""
        try:
            # Parse query parameters
            limit = int(kwargs.get('limit', 10))
            offset = int(kwargs.get('offset', 0))
            status = kwargs.get('status', '')
            year = kwargs.get('year', '')
            month = kwargs.get('month', '')
            partner_id = kwargs.get('partner_id', '')
            
            # Get current user from request (set by angkit auth method)
            user = request.env.user
            
            # Build domain for invoice search
            domain = [('move_type', 'in', ['out_invoice', 'out_refund'])]  # Only customer invoices
            
            # Check user role and apply appropriate filters
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            is_employer = user.has_group('angkot_recruitement.group_hr_recruitment_employer') or user.partner_id.is_company
            
            if is_system_admin:
                # System admin can see all invoices
                _logger.info(f"System admin {user.name} accessing all invoices")
            elif is_employer:
                # Employer can only see invoices associated with their partner
                domain.append(('partner_id', '=', user.partner_id.id))
                _logger.info(f"Employer {user.name} accessing invoices for partner {user.partner_id.id}")
            else:
                # Other users can only see their own invoices
                domain.append(('partner_id', '=', user.partner_id.id))
                _logger.info(f"User {user.name} accessing invoices for partner {user.partner_id.id}")
            
            # Apply additional filters
            if status:
                if status == 'draft':
                    domain.append(('state', '=', 'draft'))
                elif status == 'sent':
                    domain.append(('state', '=', 'posted'))
                elif status == 'paid':
                    domain.append(('state', '=', 'posted'))
                elif status == 'overdue':
                    domain.append(('state', '=', 'posted'))
                    domain.append(('invoice_date_due', '<', fields.Date.today()))
                elif status == 'cancelled':
                    domain.append(('state', '=', 'cancel'))
            
            if year:
                domain.append(('invoice_date', '>=', f'{year}-01-01'))
                domain.append(('invoice_date', '<=', f'{year}-12-31'))
            
            if month and year:
                domain.append(('invoice_date', '>=', f'{year}-{month.zfill(2)}-01'))
                if month in ['01', '03', '05', '07', '08', '10', '12']:
                    domain.append(('invoice_date', '<=', f'{year}-{month.zfill(2)}-31'))
                elif month in ['04', '06', '09', '11']:
                    domain.append(('invoice_date', '<=', f'{year}-{month.zfill(2)}-30'))
                else:  # February
                    domain.append(('invoice_date', '<=', f'{year}-{month.zfill(2)}-29'))
            
            if partner_id:
                domain.append(('partner_id', '=', int(partner_id)))
            
            # Get invoices using sudo to bypass access rights
            invoices = request.env['account.move'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='invoice_date desc, id desc'
            )
            
            # Get total count
            total_count = request.env['account.move'].sudo().search_count(domain)
            
            # Format invoice data for API response
            invoice_data = []
            for invoice in invoices:
                # Determine invoice status
                invoice_status = 'draft'
                if invoice.state == 'posted':
                    if invoice.payment_state == 'paid':
                        invoice_status = 'paid'
                    if invoice.invoice_date_due and invoice.invoice_date_due < fields.Date.today():
                        invoice_status = 'overdue'
                    else:
                        invoice_status = 'sent'
                elif invoice.state == 'cancel':
                    invoice_status = 'cancelled'
                
                # Get line items
                line_items = []
                for line in invoice.invoice_line_ids:
                    line_items.append({
                        'id': line.id,
                        'description': line.name or '',
                        'quantity': line.quantity,
                        'unit_price': line.price_unit,
                        'total_price': line.price_subtotal,
                        'job_id': line.job_id.id if hasattr(line, 'job_id') and line.job_id else None,
                        'job_title': line.job_id.name if hasattr(line, 'job_id') and line.job_id else None,
                        'package_type': line.package_type if hasattr(line, 'package_type') else None
                    })
                
                invoice_data.append({
                    'id': invoice.id,
                    'invoice_number': invoice.name or '',
                    'user_id': invoice.partner_id.id,
                    'company_name': invoice.partner_id.name or '',
                    'billing_address': invoice.partner_id.street or '',
                    'billing_email': invoice.partner_id.email or '',
                    'billing_phone': invoice.partner_id.phone or '',
                    'billing_mobile': invoice.partner_id.mobile or '',
                    'issue_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                    'due_date': invoice.invoice_date_due.isoformat() if invoice.invoice_date_due else None,
                    'status': invoice_status,
                    'subtotal': invoice.amount_untaxed,
                    'tax_amount': invoice.amount_tax,
                    'total_amount': invoice.amount_total,
                    'currency': invoice.currency_id.name or 'USD',
                    'payment_method': invoice.payment_reference or '',
                    'payment_date': invoice.invoice_date.isoformat() if invoice.payment_state == 'paid' and invoice.invoice_date else None,
                    'notes': invoice.narration or '',
                    'created_at': invoice.create_date.isoformat(),
                    'updated_at': invoice.write_date.isoformat() if invoice.write_date else invoice.create_date.isoformat(),
                    'line_items': line_items
                })
            
            return request.make_json_response({
                'success': True,
                'data': invoice_data,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'user_role': 'system_admin' if is_system_admin else ('employer' if is_employer else 'user')
            })
            
        except Exception as e:
            _logger.error(f"Error in get_invoices API: {str(e)}")
            _logger.error(f"Parameters: {kwargs}")
            return request.make_json_response({
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0,
                'limit': 10,
                'offset': 0
            }, status=500)
    
    @http.route('/api/invoices/<int:invoice_id>', type='http', auth='angkit', methods=['GET'], csrf=False)
    def get_invoice_detail(self, invoice_id, **kwargs):
        """API endpoint to get detailed invoice information"""
        try:
            # Get current user from request (set by angkit auth method)
            user = request.env.user
            
            # Get the invoice
            invoice = request.env['account.move'].sudo().browse(invoice_id)
            
            if not invoice.exists() or invoice.move_type not in ['out_invoice', 'out_refund']:
                return request.make_json_response({
                    'success': False,
                    'error': 'Invoice not found'
                }, status=404)
            
            # Check user role and access permissions
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            if not is_system_admin and invoice.partner_id.id != user.partner_id.id:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - You can only view your own invoices'
                }, status=403)
            
            # Determine invoice status
            invoice_status = 'draft'
            if invoice.state == 'posted':
                if invoice.payment_state == 'paid':
                    invoice_status = 'paid'
                elif invoice.invoice_date_due and invoice.invoice_date_due < fields.Date.today():
                    invoice_status = 'overdue'
                else:
                    invoice_status = 'sent'
            elif invoice.state == 'cancel':
                invoice_status = 'cancelled'
            
            # Get line items
            line_items = []
            for line in invoice.invoice_line_ids:
                line_items.append({
                    'id': line.id,
                    'description': line.name or '',
                    'quantity': line.quantity,
                    'unit_price': line.price_unit,
                    'total_price': line.price_subtotal,
                    'job_id': line.job_id.id if hasattr(line, 'job_id') and line.job_id else None,
                    'job_title': line.job_id.name if hasattr(line, 'job_id') and line.job_id else None,
                    'package_type': line.package_type if hasattr(line, 'package_type') else None
                })
            
            # Format invoice data for API response
            invoice_data = {
                'id': invoice.id,
                'invoice_number': invoice.name or '',
                'user_id': invoice.partner_id.id,
                'company_name': invoice.partner_id.name or '',
                'billing_address': invoice.partner_id.street or '',
                'billing_email': invoice.partner_id.email or '',
                'billing_phone': invoice.partner_id.phone or '',
                'billing_mobile': invoice.partner_id.mobile or '',
                'issue_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                'due_date': invoice.invoice_date_due.isoformat() if invoice.invoice_date_due else None,
                'status': invoice_status,
                'subtotal': invoice.amount_untaxed,
                'tax_amount': invoice.amount_tax,
                'total_amount': invoice.amount_total,
                'currency': invoice.currency_id.name or 'USD',
                'payment_method': invoice.payment_reference or '',
                'payment_date': invoice.invoice_date.isoformat() if invoice.payment_state == 'paid' and invoice.invoice_date else None,
                'notes': invoice.narration or '',
                'created_at': invoice.create_date.isoformat(),
                'updated_at': invoice.write_date.isoformat() if invoice.write_date else invoice.create_date.isoformat(),
                'line_items': line_items,
                'state': invoice.state,
                'payment_state': invoice.payment_state,
                'ref': invoice.ref or '',
                'origin': invoice.invoice_origin or ''
            }
            
            return request.make_json_response({
                'success': True,
                'data': invoice_data
            })
            
        except Exception as e:
            _logger.error(f"Error in get_invoice_detail API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @http.route('/api/partners', type='http', auth='angkit', methods=['GET'], csrf=False)
    def get_partners(self, **kwargs):
        """API endpoint to get partners (companies/customers) with role-based access control"""
        try:
            # Parse query parameters
            limit = int(kwargs.get('limit', 50))
            offset = int(kwargs.get('offset', 0))
            search = kwargs.get('search', '')
            partner_type = kwargs.get('type', '')  # 'company', 'person', or empty for all
            
            # Get current user from request (set by angkit auth method)
            user = request.env.user
            
            # Check user role - only admin users can access partners list
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            if not is_system_admin:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Only system administrators can access partners list'
                }, status=403)
            
            # Build domain for partner search
            domain = [('is_company', '=', True)]  # Only show companies by default
            
            if partner_type == 'person':
                domain = [('is_company', '=', False)]
            elif partner_type == 'all':
                domain = []  # Show both companies and individuals
            
            # Apply search filter
            if search:
                domain.append('|')
                domain.append(('name', 'ilike', search))
                domain.append(('email', 'ilike', search))
            
            # Get partners using sudo to bypass access rights
            partners = request.env['res.partner'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='name asc'
            )
            
            # Get total count
            total_count = request.env['res.partner'].sudo().search_count(domain)
            
            # Format partner data for API response
            partner_data = []
            for partner in partners:
                partner_data.append({
                    'id': partner.id,
                    'name': partner.name or '',
                    'email': partner.email or '',
                    'phone': partner.phone or '',
                    'mobile': partner.mobile or '',
                    'company': partner.name if partner.is_company else partner.parent_id.name if partner.parent_id else '',
                    'is_company': partner.is_company,
                    'street': partner.street or '',
                    'street2': partner.street2 or '',
                    'city': partner.city or '',
                    'zip': partner.zip or '',
                    'state_id': partner.state_id.id if partner.state_id else None,
                    'state_name': partner.state_id.name if partner.state_id else '',
                    'country_id': partner.country_id.id if partner.country_id else None,
                    'country_name': partner.country_id.name if partner.country_id else '',
                    'website': partner.website or '',
                    'vat': partner.vat or '',
                    'ref': partner.ref or '',
                    'active': partner.active,
                    'create_date': partner.create_date.isoformat(),
                    'write_date': partner.write_date.isoformat() if partner.write_date else partner.create_date.isoformat(),
                    'parent_id': partner.parent_id.id if partner.parent_id else None,
                    'parent_name': partner.parent_id.name if partner.parent_id else '',
                    'category_ids': [cat.id for cat in partner.category_id] if partner.category_id else [],
                    'category_names': [cat.name for cat in partner.category_id] if partner.category_id else []
                })
            
            return request.make_json_response({
                'success': True,
                'data': partner_data,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            _logger.error(f"Error in get_partners API: {str(e)}")
            _logger.error(f"Parameters: {kwargs}")
            return request.make_json_response({
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0,
                'limit': 50,
                'offset': 0
            }, status=500)
    
    @http.route('/api/partners/<int:partner_id>', type='http', auth='angkit', methods=['GET'], csrf=False)
    def get_partner_detail(self, partner_id, **kwargs):
        """API endpoint to get detailed partner information"""
        try:
            # Get current user from request (set by angkit auth method)
            user = request.env.user
            
            # Check user role - only admin users can access partner details
            is_system_admin = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
            
            if not is_system_admin:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied - Only system administrators can access partner details'
                }, status=403)
            
            # Get the partner
            partner = request.env['res.partner'].sudo().browse(partner_id)
            
            if not partner.exists():
                return request.make_json_response({
                    'success': False,
                    'error': 'Partner not found'
                }, status=404)
            
            # Format partner data for API response
            partner_data = {
                'id': partner.id,
                'name': partner.name or '',
                'email': partner.email or '',
                'phone': partner.phone or '',
                'mobile': partner.mobile or '',
                'company': partner.name if partner.is_company else partner.parent_id.name if partner.parent_id else '',
                'is_company': partner.is_company,
                'street': partner.street or '',
                'street2': partner.street2 or '',
                'city': partner.city or '',
                'zip': partner.zip or '',
                'state_id': partner.state_id.id if partner.state_id else None,
                'state_name': partner.state_id.name if partner.state_id else '',
                'country_id': partner.country_id.id if partner.country_id else None,
                'country_name': partner.country_id.name if partner.country_id else '',
                'website': partner.website or '',
                'vat': partner.vat or '',
                'ref': partner.ref or '',
                'active': partner.active,
                'create_date': partner.create_date.isoformat(),
                'write_date': partner.write_date.isoformat() if partner.write_date else partner.create_date.isoformat(),
                'parent_id': partner.parent_id.id if partner.parent_id else None,
                'parent_name': partner.parent_id.name if partner.parent_id else '',
                'category_ids': [cat.id for cat in partner.category_id] if partner.category_id else [],
                'category_names': [cat.name for cat in partner.category_id] if partner.category_id else [],
                'comment': partner.comment or '',
                'lang': partner.lang or '',
                'tz': partner.tz or '',
                'user_ids': [user.id for user in partner.user_ids] if partner.user_ids else [],
                'user_names': [user.name for user in partner.user_ids] if partner.user_ids else [],
                'supplier_rank': partner.supplier_rank,
                'customer_rank': partner.customer_rank
            }
            
            return request.make_json_response({
                'success': True,
                'data': partner_data
            })
            
        except Exception as e:
            _logger.error(f"Error in get_partner_detail API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @http.route('/api/subscriptions', type='http', auth='user', methods=['GET'], csrf=False)
    def get_subscriptions(self, **kwargs):
        """API endpoint to get user's subscription"""
        try:
            user = request.env.user
            
            # Get user's active subscription
            subscription = request.env['hr.subscription'].get_user_subscription(user.id)
            
            if not subscription:
                return request.make_json_response({
                    'success': False,
                    'error': 'No active subscription found'
                }, status=404)
            
            subscription_data = {
                'id': subscription.id,
                'user_id': subscription.user_id.id,
                'plan_id': subscription.plan_id,
                'plan_name': subscription.plan_name,
                'status': subscription.status,
                'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
                'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
                'auto_renew': subscription.auto_renew,
                'price': subscription.discounted_price or subscription.price,
                'currency': subscription.currency_id.name,
                'billing_cycle': subscription.billing_cycle,
                'features': subscription.get_plan_features()
            }
            
            return request.make_json_response({
                'success': True,
                'data': subscription_data
            })
            
        except Exception as e:
            _logger.error(f"Error in get_subscriptions API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/subscriptions', type='http', auth='user', methods=['POST'], csrf=False)
    def create_subscription(self, **kwargs):
        """API endpoint to create a new subscription"""
        try:
            user = request.env.user
            
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            plan_id = data.get('plan_id')
            billing_cycle = data.get('billing_cycle', 'monthly')
            payment_method = data.get('payment_method', 'card')
            
            if not plan_id:
                return request.make_json_response({
                    'success': False,
                    'error': 'Plan ID is required'
                }, status=400)
            
            # Validate plan_id
            valid_plans = ['basic', 'premium', 'enterprise']
            if plan_id not in valid_plans:
                return request.make_json_response({
                    'success': False,
                    'error': 'Invalid plan ID'
                }, status=400)
            
            # Create subscription using the model
            subscription = request.env['hr.subscription'].create_subscription(
                user_id=user.id,
                plan_id=plan_id,
                billing_cycle=billing_cycle,
                payment_method=payment_method
            )
            
            return request.make_json_response({
                'success': True,
                'data': {
                    'subscription_id': subscription.id,
                    'plan_id': subscription.plan_id,
                    'status': subscription.status,
                    'checkout_url': f'/checkout?subscription_id={subscription.id}',
                    'message': 'Subscription created successfully. Please complete payment to activate your plan.'
                }
            })
            
        except Exception as e:
            _logger.error(f"Error in create_subscription API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/subscriptions/<int:subscription_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_subscription(self, subscription_id, **kwargs):
        """API endpoint to update a subscription"""
        try:
            user = request.env.user
            
            # Get request data
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data)
            else:
                data = kwargs
            
            plan_id = data.get('plan_id')
            billing_cycle = data.get('billing_cycle')
            
            if not plan_id:
                return request.make_json_response({
                    'success': False,
                    'error': 'Plan ID is required'
                }, status=400)
            
            # Validate plan_id
            valid_plans = ['basic', 'premium', 'enterprise']
            if plan_id not in valid_plans:
                return request.make_json_response({
                    'success': False,
                    'error': 'Invalid plan ID'
                }, status=400)
            
            # Find the subscription record
            subscription = request.env['hr.subscription'].browse(subscription_id)
            
            if not subscription.exists():
                return request.make_json_response({
                    'success': False,
                    'error': 'Subscription not found'
                }, status=404)
            
            # Validate ownership
            if subscription.user_id.id != user.id:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            # Update the subscription
            update_vals = {
                'plan_id': plan_id
            }
            if billing_cycle:
                update_vals['billing_cycle'] = billing_cycle
            
            subscription.write(update_vals)
            
            return request.make_json_response({
                'success': True,
                'data': {
                    'subscription_id': subscription.id,
                    'plan_id': subscription.plan_id,
                    'status': subscription.status,
                    'message': 'Subscription updated successfully.'
                }
            })
            
        except Exception as e:
            _logger.error(f"Error in update_subscription API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/subscriptions/<int:subscription_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def cancel_subscription(self, subscription_id, **kwargs):
        """API endpoint to cancel a subscription"""
        try:
            user = request.env.user
            
            # Find the subscription record
            subscription = request.env['hr.subscription'].browse(subscription_id)
            
            if not subscription.exists():
                return request.make_json_response({
                    'success': False,
                    'error': 'Subscription not found'
                }, status=404)
            
            # Validate ownership
            if subscription.user_id.id != user.id:
                return request.make_json_response({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            # Cancel the subscription
            subscription.action_cancel()
            
            return request.make_json_response({
                'success': True,
                'data': {
                    'subscription_id': subscription.id,
                    'status': subscription.status,
                    'message': 'Subscription cancelled successfully.'
                }
            })
            
        except Exception as e:
            _logger.error(f"Error in cancel_subscription API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/pricing-plans', type='http', auth='public', methods=['GET'], csrf=False)
    def get_pricing_plans(self, **kwargs):
        """API endpoint to get pricing plans"""
        try:
            # Mock pricing plans data
            # In a real implementation, you would query a pricing plans model
            pricing_plans = [
                {
                    'id': 'basic',
                    'name': 'Basic Plan',
                    'description': 'Perfect for small businesses and startups',
                    'price': 99,
                    'currency': 'USD',
                    'duration_days': 30,
                    'features': [
                        'Up to 5 job postings per month',
                        'Basic job analytics',
                        'Email support',
                        'Standard job visibility',
                        'Application management'
                    ],
                    'max_jobs': 5,
                    'job_boost': False,
                    'priority_support': False,
                    'analytics': True,
                    'custom_branding': False
                },
                {
                    'id': 'premium',
                    'name': 'Premium Plan',
                    'description': 'Ideal for growing companies with active hiring',
                    'price': 299,
                    'currency': 'USD',
                    'duration_days': 30,
                    'features': [
                        'Up to 20 job postings per month',
                        'Advanced job analytics',
                        'Priority email support',
                        'Featured job placement',
                        'Job boost options',
                        'Social media sharing',
                        'Candidate screening tools'
                    ],
                    'is_popular': True,
                    'max_jobs': 20,
                    'job_boost': True,
                    'priority_support': True,
                    'analytics': True,
                    'custom_branding': False
                },
                {
                    'id': 'enterprise',
                    'name': 'Enterprise Plan',
                    'description': 'Complete solution for large organizations',
                    'price': 599,
                    'currency': 'USD',
                    'duration_days': 30,
                    'features': [
                        'Unlimited job postings',
                        'Advanced analytics dashboard',
                        '24/7 phone support',
                        'Featured job placement',
                        'Job boost options',
                        'Social media sharing',
                        'Advanced candidate screening',
                        'Custom branding',
                        'API access',
                        'Dedicated account manager'
                    ],
                    'is_featured': True,
                    'max_jobs': -1,  # Unlimited
                    'job_boost': True,
                    'priority_support': True,
                    'analytics': True,
                    'custom_branding': True
                }
            ]
            
            return request.make_json_response({
                'success': True,
                'data': pricing_plans
            })
            
        except Exception as e:
            _logger.error(f"Error in get_pricing_plans API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    @http.route('/api/candidates/<int:candidate_id>/extract-contact-info', type='http', auth='user', methods=['POST'], csrf=False)
    def extract_candidate_contact_info(self, candidate_id, **kwargs):
        """API endpoint to trigger contact info extraction for a candidate"""
        try:
            # Find the candidate
            candidate = request.env['hr.candidate'].browse(candidate_id)
            
            if not candidate.exists():
                return request.make_json_response({
                    'success': False,
                    'error': 'Candidate not found'
                }, status=404)
            
            # Check if user has permission to access this candidate
            # You might want to add additional permission checks here
            
            # Trigger extraction
            candidate.action_extract_contact_info()
            
            # Return updated candidate data
            return request.make_json_response({
                'success': True,
                'data': {
                    'id': candidate.id,
                    'partner_name': candidate.partner_name,
                    'email_from': candidate.email_from,
                    'partner_phone': candidate.partner_phone,
                    'last_extraction_date': candidate.last_extraction_date.isoformat() if candidate.last_extraction_date else None,
                    'extraction_log': candidate.extraction_log
                },
                'message': 'Contact information extracted successfully'
            })
            
        except Exception as e:
            _logger.error(f"Error in extract_candidate_contact_info API: {str(e)}")
            return request.make_json_response({
                'success': False,
                'error': 'Failed to extract contact information'
            }, status=500)

