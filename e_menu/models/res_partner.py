# -*- codig: utf-8 -*-
import uuid

from odoo import fields, models, api, _


class Partner(models.Model):
    _inherit = "res.partner"

    type = fields.Selection(selection_add=[
        ('store', 'Store')
    ])
    telegram_token = fields.Char(string='Telegram Token', readonly=True)
    telegram_chat_id = fields.Char(string="Telegram Chat ID")
    wifi_name = fields.Char(string="Wifi Name")
    wifi_password = fields.Char(string="Wifi Password")
    shop_bank_ids = fields.One2many('angkort.shop.bank', 'shop_id')
    customer_address = fields.Char()
    shop_latitude = fields.Char()
    shop_longitude = fields.Char()

    def generate_telegram_token(self):
        for partner in self:
            partner.telegram_token = str(uuid.uuid4())

    @api.model_create_multi
    def create(self, vals):
        if self._context.get('create_company'):
            for val in vals:
                val['company_type'] = 'company'
                val['type'] = 'store'
        res = super().create(vals)
        return res
