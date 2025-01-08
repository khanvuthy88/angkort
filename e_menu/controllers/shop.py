from odoo import http
from odoo.http import request
from collections import defaultdict

BASE_URL = '/angkort/api/v1'

PARTNER_FIELDS = [
    'name', 'wifi_name', 'phone', 'customer_address', 'shop_latitude', 'shop_longitude', 'email'
]

ORDER_STATE = {
    'draft': 'Quotation',
    'sent': 'Quotation Sent',
    'sale': 'Sale Order',
    'cancel': 'Cancelled'
}


class ShopController(http.Controller):

    @classmethod
    def _string_to_string_list(cls, string: str) -> list:
        """
        Returns a list of string
        :param string:
        :return:
        """
        if not string:
            return []
        string_list = string.split(',')
        return string_list

    @classmethod
    def _product_to_dict(cls, product):
        return {
            'id': product.id,
            'name': product.name,
            'code': product.default_code or '',
            'description': product.description or '',
            'sale_price': product.list_price,
            'image': product.image_512,
            'category': {
                'id': product.categ_id.id,
                'name': product.categ_id.name
            }
        }

    @classmethod
    def _category_to_dict(cls, category):
        return {
            'id': category.id,
            'name': category.name
        }

    @classmethod
    def _shop_bank_to_dict(cls, bank):
        return {
            'name': bank.name or '',
            'link': bank.link or '',
            'currency': bank.currency or '',
            'logo': bank.logo
        }

    @classmethod
    def _get_product_details(cls, product):
        product_data = cls._product_to_dict(product)
        product_data['options'] = [cls._get_product_options(option) for option in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'radio')]
        product_data['choices'] = [cls._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'multi')]
        return product_data

    @classmethod
    def _order_line_to_dict(cls, order_line):
        return {
            'id': order_line.id,
            'product_id': order_line.product_id.id,
            'name': order_line.product_id.name,
            'code': order_line.product_id.default_code or '',
            'quantity': order_line.product_uom_qty,
            'price_unit': order_line.price_unit
        }

    @classmethod
    def _get_product_options(cls, option):
        return {
            'id': option.id,
            'name': option.display_name,
            'data': [{
                'id': data.id,
                'name': data.name,
                'price': data.price_extra
            } for data in option.product_template_value_ids]
        }

    @classmethod
    def _get_product_choices(cls, choice):
        return {
            'id': choice.id,
            'name': choice.display_name,
            'data': [{
                'id': data.id,
                'name': data.name,
                'price': data.price_extra
            } for data in choice.product_template_value_ids]
        }

    @http.route(f"{BASE_URL}/my/order", auth="angkit", type="json", cors="*")
    def my_order(self):
        sales = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ])

        grouped_orders = defaultdict(list)
        for sale in sales:
            grouped_orders[sale.state].append({
                'id': sale.id,
                'name': sale.name,
                'date_order': sale.date_order.strftime('%d-%m-%Y'),
                'total': sale.amount_total,
                'state': ORDER_STATE.get(sale.state)
            })

        response = {state: orders for state, orders in grouped_orders.items()}
        return response

    @http.route(f'{BASE_URL}/my/order/<int:order_id>', auth="angkit", type="json", cors="*")
    def my_order_detail(self, order_id):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)

        if not order:
            return {
                'error': 'Order not found'
            }

        return {
            'id': order.id,
            'partner_id': order.partner_id.id,
            'partner_name': order.partner_id.name,
            'delivery_address': order.partner_id._display_address() if order.partner_shipping_id else '',
            'name': order.name,
            'date_order': order.date_order.strftime('%d-%m-%Y'),
            'total': order.amount_total,
            'state': ORDER_STATE.get(order.state),
            'order_lines': [self._order_line_to_dict(line) for line in order.order_line]
        }

    @http.route(f"{BASE_URL}/cart/checkout", auth="angkit", type="json", cors="*")
    def cart_checkout(self):
        cart_obj = request.get_json_data()
        if not cart_obj.get('cart'):
            return {
                'error': "Invalid cart object"
            }
        cart = cart_obj.get('cart')
        if not isinstance(cart, list):
            return {
                'error': "Invalid cart object",
            }
        response = {'sufficient_stock': [], 'insufficient_stock': []}
        for item in cart:
            products_sudo = request.env['product.product'].sudo()
            product = products_sudo.search([
                ('id', '=', item['product_id'])
            ], limit=1)
            if not product:
                continue
            if product.qty_available < item['quantity']:
                response['insufficient_stock'].append({
                    'product_id': product.id,
                    'code': product.default_code,
                    'name': product.name,
                    'quantity': item['quantity'],
                    'available': product.qty_available
                })
            else:
                response['sufficient_stock'].append({
                    'product_id': product.id,
                    'code': product.default_code,
                    'name': product.name,
                    'quantity': item['quantity']
                })

        if response['insufficient_stock']:
            return {
                'status': 'insufficient_stock',
                'details': response
            }
        return {
            'status': 'sufficient_stock',
            'details': response['sufficient_stock']
        }

    @http.route(f"{BASE_URL}/shop", auth="public", type="json", cors="*")
    def shop(self):
        stores_sudo = request.env['res.partner'].sudo()
        stores = stores_sudo.search([('type', '=', 'store')])
        return [{
            'id': shop.id,
            'name': shop.name or '',
            'phoneNumber': f"{self._string_to_string_list(shop.phone)}" or '',
            "address": f'[%s]' % shop.customer_address if shop.customer_address else '',
            'wifi': f"{self._string_to_string_list(shop.wifi_name)}" or '',
            'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids]
        } for shop in stores]

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", auth="public", type="json", cors="*")
    def shop_detail(self, shop_id):

        try:
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return {
                    'error': 'Shop not found'
                }
            return {
                'id': shop.id,
                'name': shop.name or '',
                'phoneNumber': f"{self._string_to_string_list(shop.phone)}" or '',
                "address": f'[%s]' % shop.customer_address if shop.customer_address else '',
                'wifi': f"{self._string_to_string_list(shop.wifi_name)}" or '',
                'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids]
            }
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=400)

    @http.route(f"{BASE_URL}/shop/create", auth="angkit", type="json", cors="*")
    def create_shop(self):
        try:
            data = request.get_json_data()
            create_data = data.get('params', {})
            if not all(key in PARTNER_FIELDS for key in create_data.keys()):
                return {
                    'status': False,
                    "message": "Missing required fields"
                }

            shop_data = request.env['res.partner'].sudo().with_context(create_company=True).create([create_data])
            if shop_data:
                request.env.user.partner_id.update({
                    'parent_id': shop_data.id
                })
            return {
                'status': True,
                'shop_data': {
                    'name': shop_data.name,
                    'id': shop_data.id
                }
            }
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=400)

    @http.route(f"{BASE_URL}/shop/update", auth="angkit", type="json", cors="*")
    def update_shop(self):
        pass

    @http.route(f"{BASE_URL}/shop/delete", auth="angkit", type="json", cors="*")
    def delete_shop(self):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", auth="public", type="json", cors="*")
    def product_detail(self, shop_id, product_id):
        product = request.env['product.template'].sudo().search([
            ('id', '=', product_id),
            ('shop_id', '=', shop_id)
        ], limit=1)
        if not product:
            return {
                'error': 'Product not found'
            }
        response = self._get_product_details(product)
        return response

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", auth="public", type="json", cors="*")
    def product(self, shop_id):
        products = request.env['product.product'].sudo().search([('shop_id', '=', shop_id)])
        return [self._product_to_dict(product) for product in products]

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/create", auth="angkit", type="json", cors="*")
    def create_product(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/update", auth="angkit", type="json", cors="*")
    def update_product(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/delete", auth="angkit", type="json", cors="*")
    def delete_product(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", auth="public", type="json", cors="*")
    def product_category(self, shop_id):
        categories = request.env['product.category'].sudo().searh([('shop_id', '=', shop_id)])
        return [self._category_to_dict(cate) for cate in categories]

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/create", auth="angkit", type="json", cors="*")
    def create_product_category(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/update", auth="angkit", type="json", cors="*")
    def update_product_category(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/delete", auth="angkit", type="json", cors="*")
    def delete_product_category(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", auth="public", type="json", cors="*")
    def product_variant(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/create", auth="angkit", type="json", cors="*")
    def create_product_variant(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/update", auth="angkit", type="json", cors="*")
    def update_product_variant(self, shop_id):
        pass

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/delete", auth="angkit", type="json", cors="*")
    def delete_product_variant(self, shop_id):
        pass
