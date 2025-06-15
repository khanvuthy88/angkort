from odoo import http
from odoo.http import request

BASE_URL = '/angkort/api/v1'


class HrController(http.Controller):

    def skill_by_employee(self, employee_id) -> dict[str, list]:
        """Retrieve and group skills for a specific employee.

        This method fetches all skills associated with an employee and groups them
        by their skill type. Each skill includes its ID, name, and level progress.

        Args:
            employee_id: The employee record to fetch skills for.

        Returns:
            dict[str, list]: A dictionary where:
                - Keys are skill type names (e.g., 'Technical', 'Soft Skills')
                - Values are lists of skill dictionaries containing:
                    - id (int): Skill record ID
                    - name (str): Name of the skill
                    - level_progress (int): Progress level of the skill (0-100)

        Example:
            {
                'Technical': [
                    {'id': 1, 'name': 'Python', 'level_progress': 80},
                    {'id': 2, 'name': 'JavaScript', 'level_progress': 60}
                ],
                'Soft Skills': [
                    {'id': 3, 'name': 'Communication', 'level_progress': 90}
                ]
            }
        """
        employee = request.env['hr.employee'].sudo().search([('id', '=', employee_id.id)])
        grouped_data = {}
        for skill in employee.employee_skill_ids:
            display_type = skill.skill_type_id.name
            if display_type not in grouped_data:
                grouped_data[display_type] = []
            skill_data = {
                'id': skill.id or 0,
                'name': skill.skill_id.name or '',
                'level_progress': skill.level_progress or 0,
            }
            grouped_data[display_type].append(skill_data)
        return grouped_data

    def resume_by_employee(self, employee_id) -> dict[str, list]:
        """Retrieve and group resume entries for a specific employee.

        This method fetches all resume entries associated with an employee and groups them
        by their line type (e.g., 'Experience', 'Education', 'Certification').
        Each entry includes its ID, name, date range, and description.

        Args:
            employee_id: The employee record to fetch resume entries for.

        Returns:
            dict[str, list]: A dictionary where:
                - Keys are resume line type names (e.g., 'Experience', 'Education')
                - Values are lists of resume entry dictionaries containing:
                    - id (int): Resume line record ID
                    - name (str): Title or name of the entry
                    - date_start (str): Start date in DD-MM-YYYY format
                    - date_end (str): End date in DD-MM-YYYY format
                    - description (str): Detailed description of the entry

        Example:
            {
                'Experience': [
                    {
                        'id': 1,
                        'name': 'Senior Developer',
                        'date_start': '01-01-2020',
                        'date_end': '31-12-2022',
                        'description': 'Led development team...'
                    }
                ],
                'Education': [
                    {
                        'id': 2,
                        'name': 'Bachelor of Science',
                        'date_start': '01-09-2015',
                        'date_end': '30-06-2019',
                        'description': 'Computer Science'
                    }
                ]
            }
        """
        employee = request.env['hr.employee'].sudo().search([('id', '=', employee_id.id)])
        grouped_data = {}
        for resume in employee.resume_line_ids:
            display_type = resume.line_type_id.name
            if display_type not in grouped_data:
                grouped_data[display_type] = []
            resume_data = {
                'id': resume.id or 0,
                'name': resume.name or '',
                'date_start': resume.date_start and resume.date_start.strftime('%d-%m-%Y') or '',
                'date_end': resume.date_end and resume.date_end.strftime('%d-%m-%Y') or '',
                'description': resume.description or ''
            }
            grouped_data[display_type].append(resume_data)
        return grouped_data

    @http.route(f'{BASE_URL}/employee/detail', type="json", methods=["POST"], auth="public", csrf=False)
    def employee_detail(self):
        """Retrieve detailed information about an employee.

        This endpoint fetches comprehensive employee information including personal details,
        contact information, job details, and optionally resume and skills.

        Request:
            POST /angkort/api/v1/employee/detail
            {
                "employee_id": int,  # Required: ID of the employee
                "include_resume": bool,  # Optional: Whether to include resume information
                "include_skills": bool   # Optional: Whether to include skills information
            }

        Returns:
            dict: Employee information with the following structure:
                {
                    "id": int,
                    "name": str,
                    "birthday": str,  # Format: DD-MM-YYYY
                    "avatars": {
                        "128": str,   # Base64 encoded image
                        "256": str,
                        "512": str,
                        "1024": str,
                        "1920": str
                    },
                    "department": {
                        "id": int,
                        "name": str
                    },
                    "contact_info": {
                        "email": str,
                        "phone": str,
                        "emergency": {
                            "name": str,
                            "phone": str
                        }
                    },
                    "personal_info": {
                        "gender": str,
                        "place_of_birth": str,
                        "marital": str,
                        "identification_id": str
                    },
                    "location": {
                        "country": {
                            "id": int,
                            "name": str
                        }
                    },
                    "job_info": {
                        "title": str,
                        "position": {
                            "id": int,
                            "name": str
                        },
                        "manager": {
                            "id": int,
                            "name": str
                        }
                    },
                    "resume": list,  # Optional: Only included if include_resume is True
                    "skills": list   # Optional: Only included if include_skills is True
                }

        Raises:
            dict: Error response if employee_id is missing or employee not found
                {
                    "error": str  # Error message
                }

        Performance:
            - Uses browse instead of search for direct ID access
            - Prefetches related fields to minimize database queries
            - Conditionally loads resume and skills data
        """
        data = request.get_json_data()
        employee_id = data.get('employee_id', False)
        
        if not employee_id:
            return {'error': 'Employee ID is required'}
            
        # Use browse instead of search when we have the ID
        emp = request.env['hr.employee'].sudo().browse(employee_id)
        
        if not emp.exists():
            return {'error': 'Employee not found'}
            
        # Prefetch related fields to reduce database queries
        emp.mapped('department_id')
        emp.mapped('country_id')
        emp.mapped('job_id')
        emp.mapped('parent_id')
        
        # Use dictionary comprehension for cleaner code
        response = {
            'id': emp.id,
            'name': emp.name,
            'birthday': emp.birthday and emp.birthday.strftime('%d-%m-%Y') or '',
            'avatars': {
                '128': emp.avatar_128 or '',
                '256': emp.avatar_256 or '',
                '512': emp.avatar_512 or '',
                '1024': emp.avatar_1024 or '',
                '1920': emp.avatar_1920 or '',
            },
            'department': {
                'id': emp.department_id.id or 0,
                'name': emp.department_id.name or ''
            } if emp.department_id else {},
            'contact_info': {
                'email': emp.email or '',
                'phone': emp.phone or '',
                'emergency': {
                    'name': emp.emergency_contact or '',
                    'phone': emp.emergency_phone or '',
                }
            },
            'personal_info': {
                'gender': emp.gender or '',
                'place_of_birth': emp.place_of_birth or '',
                'marital': emp.marital,
                'identification_id': emp.identification_id or '',
            },
            'location': {
                'country': {
                    'id': emp.country_id.id or 0,
                    'name': emp.country_id.name or ''
                } if emp.country_id else {}
            },
            'job_info': {
                'title': emp.job_title or '',
                'position': {
                    'id': emp.job_id.id or 0,
                    'name': emp.job_id.name or ''
                } if emp.job_id else {},
                'manager': {
                    'id': emp.parent_id.id,
                    'name': emp.parent_id.name
                } if emp.parent_id else {}
            }
        }
        
        # Add resume and skills only if needed
        if data.get('include_resume', False):
            response['resume'] = self.resume_by_employee(emp)
            
        if data.get('include_skills', False):
            response['skills'] = self.skill_by_employee(emp)
            
        return response

    @http.route(f"{BASE_URL}/employee", type="json", methods=["GET"], auth="public", csrf=False)
    def employee(self):
        """Retrieve a paginated list of employees with filtering and search capabilities.

        This endpoint provides a flexible way to fetch employee information with support for
        pagination, filtering, and search functionality. It's optimized for performance with
        efficient database queries and minimal data transfer.

        Request:
            GET /angkort/api/v1/employee
            Query Parameters:
                page (int): Page number for pagination (default: 1)
                limit (int): Number of records per page (default: 20, max: 100)
                department_id (int): Filter by department ID
                job_id (int): Filter by job position ID
                manager_id (int): Filter by manager ID
                search (str): Search term for employee name or ID

        Returns:
            dict: Paginated employee list with the following structure:
                {
                    "total": int,  # Total number of records
                    "page": int,   # Current page number
                    "limit": int,  # Records per page
                    "pages": int,  # Total number of pages
                    "employees": [
                        {
                            "id": int,
                            "name": str,
                            "job_title": str,
                            "department_id": {
                                "id": int,
                                "name": str
                            },
                            "job_id": {
                                "id": int,
                                "name": str
                            },
                            "parent_id": {
                                "id": int,
                                "name": str
                            },
                            "mobile_phone": str,
                            "work_email": str,
                            "image_1920": str  # Base64 encoded image
                        }
                    ]
                }

        Examples:
            # Get first page of employees
            GET /angkort/api/v1/employee?page=1&limit=20

            # Search employees in department 1
            GET /angkort/api/v1/employee?department_id=1&search=john

            # Get employees under manager 5
            GET /angkort/api/v1/employee?manager_id=5&page=1&limit=50

        Performance:
            - Uses domain filtering for efficient database queries
            - Implements pagination to limit result set size
            - Prefetches related fields to minimize database queries
            - Uses sudo() for proper access rights
            - Limits maximum records per page to prevent overload

        Security:
            - Uses sudo() for proper access rights
            - Validates and sanitizes input parameters
            - Limits maximum records per page to prevent DoS

        Notes:
            - All ID fields default to 0 if not found
            - All string fields default to empty string if not found
            - Search is case-insensitive and matches partial names
            - Image is returned as base64 encoded string
        """
        # Get query parameters with defaults
        page = int(request.httprequest.args.get('page', 1))
        limit = min(int(request.httprequest.args.get('limit', 20)), 100)  # Cap at 100 records
        department_id = request.httprequest.args.get('department_id')
        job_id = request.httprequest.args.get('job_id')
        manager_id = request.httprequest.args.get('manager_id')
        search = request.httprequest.args.get('search')

        # Build domain for filtering
        domain = []
        if department_id:
            domain.append(('department_id', '=', int(department_id)))
        if job_id:
            domain.append(('job_id', '=', int(job_id)))
        if manager_id:
            domain.append(('parent_id', '=', int(manager_id)))
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', f'%{search}%'))
            domain.append(('id', '=', search))

        # Get total count for pagination
        total = request.env['hr.employee'].sudo().search_count(domain)
        
        # Calculate pagination
        pages = (total + limit - 1) // limit
        page = min(max(1, page), pages) if pages > 0 else 1
        offset = (page - 1) * limit

        # Fetch employees with related fields
        employees = request.env['hr.employee'].sudo().search(
            domain,
            offset=offset,
            limit=limit,
            order='name asc'
        )

        # Prefetch related fields
        employees.mapped('department_id')
        employees.mapped('job_id')
        employees.mapped('parent_id')

        # Prepare response
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "employees": [{
                "id": emp.id,
                "name": emp.name,
                "job_title": emp.job_title or '',
                "department_id": {
                    "id": emp.department_id.id or 0,
                    "name": emp.department_id.name or ''
                } if emp.department_id else {},
                "job_id": {
                    "id": emp.job_id.id or 0,
                    "name": emp.job_id.name or ''
                } if emp.job_id else {},
                "parent_id": {
                    "id": emp.parent_id.id or 0,
                    "name": emp.parent_id.name or ''
                } if emp.parent_id else {},
                "mobile_phone": emp.mobile_phone or '',
                "work_email": emp.work_email or '',
                "image_1920": emp.image_1920 or ''
            } for emp in employees]
        }
