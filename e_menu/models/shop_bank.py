# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ShopBank(models.Model):
    _name = 'angkort.shop.bank'
    _description = "E-Menu bank"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10)
    shop_id = fields.Many2one('res.partner')
    currency_id = fields.Char(string="Currency", required=True)
    link = fields.Char()
    logo = fields.Binary()
    code = fields.Char(string="Code", required=True)
    active = fields.Boolean(string="Active", default=True)