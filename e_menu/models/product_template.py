
from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    shop_id = fields.Many2one('res.partner', domain="[('type', '=', 'store')]")
