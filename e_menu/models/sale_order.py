# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shop_id = fields.Many2one(
        'res.partner',
        string='Shop',
        domain=[('type', '=', 'store')],
        help='The shop/store where this order originates from',
        ondelete='set null',
        tracking=True
    )

