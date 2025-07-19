# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class angkort-jwt-auth(models.Model):
#     _name = 'angkort-jwt-auth.angkort-jwt-auth'
#     _description = 'angkort-jwt-auth.angkort-jwt-auth'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

