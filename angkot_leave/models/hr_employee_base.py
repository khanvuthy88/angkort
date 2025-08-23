
from pytz import timezone, UTC, utc
from datetime import timedelta, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_time


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    telegram_user_id = fields.Char()