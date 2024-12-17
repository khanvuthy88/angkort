# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ShopBank(models.Model):
    _name = 'shop.bank'

    name = fields.Char(string="Name", required=True)
    shop_id = fields.Many2one('res.partner')
    currency_id = fields.Char(string="Currency", required=True)
    link = fields.Char()
    logo = fields.Binary()
    code = fields.Char(string="Code", required=True)
    active = fields.Boolean(string="Active", default=True)