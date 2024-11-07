# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request
from odoo import fields

BASE_URL = '/angkort/api/v1'
SALE_STATE = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'sale': 'Sale Order',
    'cancel': 'Cancelled'
}


class EMenu(http.Controller):
    @http.route(f'{BASE_URL}/product/list', auth='public', type="json")
    def product_list(self):
        """
        Returns a list of products with details such as ID, name, code, sale price,
        and category information in JSON format.

        The route for this endpoint is `BASE_URL/product/list`, and it is publicly accessible.
        """
        products = request.env['product.template'].sudo().search([])
        return [{
            'id': product.id,
            'name': product.name,
            'code': product.default_code,
            'sale_price': product.list_price,
            # 'image': product.image_1920,
            'category': {
                'id': product.categ_id.id,
                'name': product.categ_id.name
            }
        } for product in products]

    @http.route(f"{BASE_URL}/sale/list", auth="public", type="json")
    def sale_order(self):

        """
        Returns a list of sales orders with details such as ID, name, state, order date,
        customer information, salesman information, sales team information, order lines,
        and total in JSON format.

        The route for this endpoint is `BASE_URL/sale/list`, and it is publicly accessible.
        """
        sale_orders = request.env['sale.order'].sudo().search([])
        return [{
            'id': sale.id,
            'name': sale.name,
            'state': SALE_STATE.get(sale.state),
            'order_date': sale.date_order.strftime('%d-%m-%Y'),
            'customer': sale.partner_id.name,
            'salesman': sale.user_id.name,
            'sale_team': sale.team_id.name,
            'order_lines': [{
                'product': {
                    'id': line.product_id.id,
                    'name': line.product_id.name
                },
                'qty': line.product_uom_qty,
                'unit_price': line.price_unit,
                'total': line.price_subtotal
            } for line in sale.order_line],
            'total': sale.tax_totals
        } for sale in sale_orders]

    @http.route(f"{BASE_URL}/order/new", auth="public", type="json", methods=["POST"])
    def new_order(self):
        data = json.loads(request.httprequest.data.decode('utf-8'))
        print(data)
        partner_id = data['params'].get('customer_id', 0)
        print(partner_id)
        order_date = data['params'].get('order_date', '')
        order_date = fields.Datetime.now()
        order_line = data['params'].get('order_line', [])
        sale_order = request.env['sale.order'].sudo().create({
            'partner_id': partner_id,
            'date_order': order_date,
            'order_line': [
                (0, 0, {
                    'product_id': line['product_id'],
                    'product_uom_qty': line['quantity'],
                    'price_unit': line['price_unit'],
                })
                for line in order_line
            ]
        })

        return {"success": True, "sale_order_id": sale_order.id}
