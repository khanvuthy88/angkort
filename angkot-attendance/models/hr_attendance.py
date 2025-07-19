from odoo import fields, models, api, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_lat = fields.Char()
    check_in_lng = fields.Char()
    check_out_lat = fields.Char()
    check_out_lng = fields.Char()
    radius = fields.Char()
