from odoo import fields, models, api, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_lat = fields.Char()
    check_in_long = fields.Char()
    check_out_lat = fields.Char()
    check_out_long = fields.Char()
    radius = fields.Char()

    check_in_note = fields.Char()
    check_in_photo = fields.Image()

    check_out_note = fields.Char()
    check_out_photo = fields.Image()
    in_mode = fields.Selection(
        selection_add=[('mobile', 'Mobile')]
    )
    out_mode = fields.Selection(selection_add=[('mobile', 'Mobile')])

    @api.model_create_multi
    def create(self, values):
        for val in values:
            if 'in_mode' == 'mobile':
                check_in_date = fields.Datetime.fromstring(val['check_in'])
                val['check_in'] = check_in_date
        return super().create(values)

