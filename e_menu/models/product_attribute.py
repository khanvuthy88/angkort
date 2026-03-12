from odoo import fields, models, api, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    shop_id = fields.Many2one('res.partner', domain="[('type', '=', 'store')]")

    # Override the base unique(name) constraint so that different shops can
    # each have an attribute with the same name (e.g. both Shop A and Shop B
    # can have "Color"). Uniqueness is now enforced per (name, shop_id) pair.
    _sql_constraints = [
        ('name_uniq', 'unique(name, shop_id)', 'An attribute with this name already exists for this shop.'),
    ]
