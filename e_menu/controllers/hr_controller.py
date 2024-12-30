from odoo import http
from odoo.http import request

BASE_URL = '/angkort/api/v1'


class HrController(http.Controller):

    def skill_by_employee(self, employee_id) -> dict[str, list]:
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

    @http.route(f"{BASE_URL}/employee", type="json", methods=["GET"], auth="public", csrf=False)
    def employee_list(self):
        employees = request.env['hr.employee'].sudo().search([])
        return [
            {
                'id': emp.id,
                'name': emp.name,
                'birthday': emp.birthday and emp.birthday.strftime('%d-%m-%Y') or '',
                'avatar_128': emp.avatar_128 or '',
                'avatar_256': emp.avatar_256 or '',
                'avatar_512': emp.avatar_512 or '',
                'avatar_1024': emp.avatar_1024 or '',
                'avatar_1920': emp.avatar_1920 or '',
                'department_id': {
                    'id': emp.department_id.id or 0,
                    'name': emp.department_id.name or ''
                } if emp.department_id else {},
                'email': emp.email or '',
                'phone': emp.phone or '',
                'gender': emp.gender or '',
                'place_of_birth': emp.place_of_birth or '',
                'emergency_contact': {
                    'contact_name': emp.emergency_contact or '',
                    'contact_phone': emp.emergency_phone or '',
                },
                'country_id': {
                    'id': emp.country_id.id or 0,
                    'name': emp.country_id.name or ''
                } if emp.country_id else {},
                'identification_id': emp.identification_id or '',
                'job_id': {
                    'id': emp.job_id.id or 0,
                    'name': emp.job_id.name or ''
                } if emp.job_id else {},
                'job_title': emp.job_title or '',
                'marital': emp.marital,
                'manager_id': {
                    'id': emp.parent_id.id,
                    'name': emp.parent_id.name
                } if emp.parent_id else {},
                'resume_line_ids': self.resume_by_employee(emp),
                'skill_ids': self.skill_by_employee(emp),
            } for emp in employees
        ]
