 # -*- codig: utf-8 -*-

from odoo import fields, models, api, _


class Partner(models.Model):
     _inherit = "res.partner"

     type = fields.Selection(selection_add=[
          ('store', 'Store')
     ])
     wifi_name = fields.Char(string="Wifi Name")
     wifi_password = fields.Char(string="Wifi Password")
     bank_ids = fields.One2many('shop.bank', 'shop_id')
     customer_address = fields.Char()
     shop_latitude = fields.Char()
     shop_longitude = fields.Char()

     def create(self, vals):
          if self._context.get('create_company'):
               for val in vals:
                    val['company_type'] = 'company'
          res = super().create(vals)

          return res
