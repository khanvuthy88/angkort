from odoo import fields, models, api, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    shop_id = fields.Many2one('res.partner', domain="[('type', '=', 'store')]")
