import base64

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
        product_data['options'] = [cls._get_product_options(option) for option in product.attribute_line_ids.filtered(
            lambda x: x.attribute_id.display_type == 'radio')]
        product_data['choices'] = [cls._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(
            lambda x: x.attribute_id.display_type == 'multi')]
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

        product_ids = [item['product_id'] for item in cart if 'product_id' in item]
        if not product_ids:
            return {
                'error': "Cart contains no valid products"
            }
        product_sudo = request.env['product.template'].sudo()
        products = product_sudo.search([('id', 'in', product_ids)])
        product_mapped = {product.id: product for product in products}
        response = {'sufficient_stock': [], 'insufficient_stock': []}
        total_amount = 0.00

        for item in cart:
            product = product_mapped.get(item['product_id'])
            if not product:
                continue
            subtotal = item.get('quantity', 0) * product.list_price
            total_amount += subtotal
            if product.qty_available < item.get('quantity', 0):
                response['insufficient_stock'].append({
                    'product_id': product.id,
                    'code': product.default_code,
                    'name': product.name,
                    'quantity': item['quantity'],
                    'available': product.qty_available,
                    'sub_total': subtotal
                })
            else:
                response['sufficient_stock'].append({
                    'product_id': product.id,
                    'code': product.default_code,
                    'name': product.name,
                    'quantity': item['quantity'],
                    'sub_total': subtotal
                })

        if response['insufficient_stock']:
            return {
                'status': 'insufficient_stock',
                'details': response,
                'total_amount': total_amount
            }
        return {
            'status': 'sufficient_stock',
            'details': response['sufficient_stock'],
            'total_amount': total_amount
        }

    @http.route(f"{BASE_URL}/shop", auth="public", type="json", cors="*")
    def shop(self):
        stores_sudo = request.env['res.partner'].sudo()
        stores = stores_sudo.search([('type', '=', 'store')])
        return [{
            'id': shop.id,
            'name': shop.name or '',
            'phoneNumber': self._string_to_string_list(shop.phone) or [],
            "address": [shop.customer_address] if shop.customer_address else [],
            'wifi': self._string_to_string_list(shop.wifi_name) or [],
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
                'phoneNumber': self._string_to_string_list(shop.phone) or [],
                "address": [shop.customer_address] if shop.customer_address else [],
                'wifi': self._string_to_string_list(shop.wifi_name) or [],
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
        data = request.get_json_data()
        if not data:
            return {
                'status': False,
                "message": "No data provided for update"
            }
        shop_id = data.get('id')
        if not shop_id:
            return {
                'status': False,
                "message": "Shop ID is required for update"
            }

        shop_sudo = request.env['res.partner'].sudo().search([('id', '=', shop_id)], limit=1)
        if not shop_sudo:
            return {
                'status': False,
                "message": "Shop with ID {} not found".format(shop_id)
            }
        update_fields = {key: value for key, value in data.items() if key != 'id' and hasattr(shop_sudo, key)}
        if not update_fields:
            return {
                'status': False,
                "message": "No valid fields to update"
            }

        try:
            shop_sudo.write(update_fields)
            return {
                'status': True,
                "message": "Shop with ID {} updated successfully".format(shop_id)
            }
        except Exception as e:
            return {
                'status': False,
                "message": f"Error updating shop with ID {shop_id}: {str(e)}"
            }

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
        data = []
        for product in products:
            tmp_data = self._product_to_dict(product)
            tmp_data['options'] = [self._get_product_options(option) for option in
                                   product.attribute_line_ids.filtered(
                                       lambda x: x.attribute_id.display_type == 'radio')]
            tmp_data['choices'] = [self._get_product_choices(choice) for choice in
                                   product.attribute_line_ids.filtered(
                                       lambda x: x.attribute_id.display_type == 'multi')]
            data.append(tmp_data)
        return data

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/create", auth="angkit", type="http", methods=["POST"], csrf=False, cors="*")
    def create_product(self, shop_id, **kwargs):
        image_file = request.httprequest.files['image']
        data = request.httprequest.form
        required_fields = ['name', 'price', 'category_id']

        # Validate required fields for product creation
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return request.make_json_response({'error': f'Missing required fields: {", ".join(missing_fields)}'}, status=400)


        shop_sudo = request.env['res.partner'].sudo().search([
            ('id', '=', shop_id),
            ('type', '=', 'store')
        ], limit=1)
        if not shop_sudo:
            return request.make_json_response({
                'status': False,
                'message': f"Shop with ID {shop_id} is not found"
            }, status=404)
        category = request.env['product.category'].sudo().search([('id', '=', data.get('category_id'))], limit=1)
        if not category:
            return request.make_json_response({
                "status": False,
                "message": f"Category with ID {data.get('category_id')} not found"
            }, status=404)

        # Prepare product data
        product_data = {
            'name': data.get('name'),
            'list_price': data.get('price'),
            'categ_id': category.id,
            'shop_id': shop_id,
        }
        optional_fields = ['description', 'barcode', 'qty_available']
        for field in optional_fields:
            if field in data:
                product_data[field] = data.get(field)

        try:
            # Create the product
            product = request.env['product.product'].with_user(request.env.user).create(product_data)
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                product.write({'image_1920': encoded_image})
            return request.make_json_response({
                'status': True,
                "message": "Product created successfully"
            }, status=201)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                "message": f"Error creating product: {str(e)}"
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/update", auth="angkit", type="http", methods=["POST"], csrf=False, cors="*")
    def update_product(self, shop_id, product_id):
        image_file = request.httprequest.files['image']
        shop_sudo = request.env['res.partner'].sudo().search([
            ('id', '=', shop_id),
            ('type', '=', 'store')
        ], limit=1)
        if not shop_sudo:
            return request.make_json_response({
                'status': 'error',
                'message': f'Shop with ID {shop_id} not found',
            }, status=404)

        data = request.httprequest.form
        # Validate required fields for product creation
        required_fields = ['name', 'price', 'category_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return request.make_json_response({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}',
            }, status=400)

        if 'category_id' in data:
            category = request.env['product.category'].sudo().search([('id', '=', data.get('category_id'))], limit=1)
            if not category:
                return request.make_json_response({
                    'status': 'error',
                    'message': f'Category with ID {data.get("category_id")} not found',
                }, status=404)

        # Prepare product data
        product_data = {
            'name': data.get('name'),
            'list_price': data.get('price'),
            # 'categ_id': data.get('category_id'),
            'shop_id': shop_id,  # Associate product with the shop
        }

        # Optional fields
        optional_fields = ['description', 'barcode', 'qty_available']
        for field in optional_fields:
            if field in data:
                product_data[field] = data[field]
        try:
            product = request.env['product.product'].sudo().search([
                ('id', '=', product_id), ('shop_id', '=', shop_id)
            ], limit=1)
            if not product:
                return request.make_json_response({
                    'status': 'error',
                    'message': f'Product with ID {product_id} not found',
                }, status=404)

            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                product_data['image_1920'] = encoded_image

            product.with_user(request.env.user).write(product_data)
            return request.make_json_response({
                'status': 'success',
                'message': 'Product updated successfully',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': product.list_price,
                    'category_id': product.categ_id.id,
                },
            }, status=200)
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error updating product: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/delete", auth="angkit", type="json", cors="*")
    def delete_product(self, shop_id, product_id):
        shop_sudo = request.env['res.partner'].sudo().search([
            ('id', '=', shop_id),
            ('type', '=', 'store')
        ], limit=1)
        if not shop_sudo:
            return {
                'status': 'error',
                'message': f'Shop with ID {shop_id} not found',
            }

        product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
        if not product:
            return {
                'status': 'error',
                'message': f'Product with ID {product_id} not found',
            }
        try:
            product.unlink()
            return {
                'status': 'success',
                'message': 'Product deleted successfully',
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error deleting product: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", auth="public", type="json", cors="*")
    def product_category(self, shop_id):
        categories = request.env['product.category'].sudo().searh([('shop_id', '=', shop_id)])
        return [self._category_to_dict(cate) for cate in categories]

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/create", auth="angkit", type="json", cors="*")
    def create_product_category(self, shop_id):
        data = request.get_json_data()
        if 'name' not in data:
            return {
                'status': 'error',
                'message': 'Category name is required',
            }
        try:
            category = request.env['product.category'].with_user(request.env.user).create({
                'name': data['name'],
                'shop_id': shop_id,
            })
            return {
                'status': 'success',
                'message': 'Category created successfully',
                'category': self._category_to_dict(category),
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error creating category: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>/update", auth="angkit", type="json", cors="*")
    def update_product_category(self, shop_id, cate_id):
        data = request.get_json_data()
        required_fields = ['name', 'shop_id']
        if any(field not in data for field in required_fields):
            return {
                'status': 'error',
                'message': 'Missing required fields',
            }
        try:
            category = request.env['product.category'].with_user(request.env.user).search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if category.create_uid != request.env.user:
                return {
                    'status': 'error',
                    'message': 'You are not authorized to update this category',
                }
            category.write(data)
            return {
                'status': 'success',
                'message': 'Category updated successfully',
                'category': self._category_to_dict(category),
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error updating category: {str(e)}',
            }


    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>/delete", auth="angkit", type="json", cors="*")
    def delete_product_category(self, shop_id, cate_id):
        category = request.env['product.category'].with_user(request.env.user).search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
        if not category:
            return {
                'status': 'error',
                'message': f'Category with ID {cate_id} not found',
            }
        if category.create_uid != request.env.user:
            return {
                'status': 'error',
                'message': 'You are not authorized to delete this category',
            }
        try:
            category.unlink()
            return {
                'status': 'success',
                'message': 'Category deleted successfully',
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error deleting category: {str(e)}',
            }

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
