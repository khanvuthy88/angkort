
from odoo import fields, models, api, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    shop_id = fields.Many2one('res.partner', domain="[('type', '=', 'store')]", string="Shop")
