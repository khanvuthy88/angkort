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
    shop_wifi_ids = fields.One2many('shop.wifi', 'shop_id')
    shop_open_hour_ids = fields.One2many('shop.open.hour', 'shop_id')
    shop_banner = fields.Image()
    product_count = fields.Integer(
        string='Products',
        compute='_compute_product_count',
    )
    variant_count = fields.Integer(
        string='Variants',
        compute='_compute_variant_count',
    )

    def _compute_product_count(self):
        for partner in self:
            if partner.type == 'store':
                partner.product_count = self.env['product.template'].search_count([
                    ('shop_id', '=', partner.id)
                ])
            else:
                partner.product_count = 0

    def _compute_variant_count(self):
        for partner in self:
            if partner.type == 'store':
                partner.variant_count = self.env['product.attribute'].search_count([
                    ('shop_id', '=', partner.id)
                ])
            else:
                partner.variant_count = 0

    def action_open_shop_variants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shop Variants'),
            'res_model': 'product.attribute',
            'view_mode': 'list,form',
            'domain': [('shop_id', '=', self.id)],
            'context': {'default_shop_id': self.id},
        }

    def action_open_shop_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shop Products'),
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('shop_id', '=', self.id)],
            'context': {'default_shop_id': self.id},
        }

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

class ShopWifi(models.Model):
    _name= "shop.wifi"

    name = fields.Char(required=True)
    password = fields.Char(required=True)
    wifi_qr_code = fields.Image()
    shop_id = fields.Many2one('res.partner')


class ShopOpenHour(models.Model):
    _name = "shop.open.hour"
    _description = "Shop OpenHour"

    day = fields.Selection(
        selection=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
        ],
        string='Day of Week',
        required=True
    )
    open = fields.Char(
        string='Opening Time',
        help="Time when the business opens (e.g., '9:00 AM')",
    )
    close = fields.Char(
        string='Closing Time',
        help="Time when the business closes (e.g., '5:00 PM')",
    )
    shop_id = fields.Many2one('res.partner')
