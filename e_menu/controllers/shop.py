import base64
import json

from odoo import http, Command
from odoo.http import request, Response
from collections import defaultdict
from werkzeug.exceptions import NotFound, BadRequest

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

    @http.route(f"{BASE_URL}/my/order", auth="angkit", type="http", methods=["GET"], cors="*")
    def my_order(self, **kwargs):
        try:
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', 20)), 100)
            offset = (page - 1) * limit
            fields = ['id', 'name', 'date_order', 'amount_total', 'state']
            domain = [('partner_id', '=', request.env.user.partner_id.id)]
            total = request.env['sale.order'].sudo().search_count(domain)
            pages = (total + limit - 1) // limit
            page = min(max(1, page), pages) if pages > 0 else 1
            sales = request.env['sale.order'].sudo().search(
                domain,
                fields=fields,
                offset=offset,
                limit=limit,
                order='date_order desc'
            )
            sales_data = sales.read(fields)
            grouped_orders = defaultdict(list)
            for sale in sales_data:
                grouped_orders[sale['state']].append({
                    'id': sale['id'],
                    'name': sale['name'],
                    'date_order': sale['date_order'].strftime('%d-%m-%Y') if sale['date_order'] else '',
                    'total': sale['amount_total'],
                    'state': ORDER_STATE.get(sale['state'])
                })
            response = {
                'orders': {state: orders for state, orders in grouped_orders.items()},
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': pages
                }
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f'{BASE_URL}/my/order/<int:order_id>', auth="angkit", type="http", methods=["GET"], cors="*")
    def my_order_detail(self, order_id, **kwargs):
        try:
            order = request.env['sale.order'].sudo().search([
                ('id', '=', order_id),
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)
            if not order:
                return request.make_json_response({'error': 'Order not found'}, status=404)
            return request.make_json_response({
                'id': order.id,
                'partner_id': order.partner_id.id,
                'partner_name': order.partner_id.name,
                'delivery_address': order.partner_id._display_address() if order.partner_shipping_id else '',
                'name': order.name,
                'date_order': order.date_order.strftime('%d-%m-%Y'),
                'total': order.amount_total,
                'state': ORDER_STATE.get(order.state),
                'order_lines': [self._order_line_to_dict(line) for line in order.order_line]
            }, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/cart/checkout", auth="angkit", type="json", methods=["POST"], cors="*")
    def cart_checkout(self):
        try:
            cart_obj = request.get_json_data()
            if not cart_obj.get('cart') or not isinstance(cart_obj.get('cart'), list):
                return request.make_json_response({'error': "Invalid cart object"}, status=400)
            cart = cart_obj.get('cart')
            product_ids = [item['product_id'] for item in cart if 'product_id' in item]
            if not product_ids:
                return request.make_json_response({'error': "Cart contains no valid products"}, status=400)
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
                return request.make_json_response({
                    'status': 'insufficient_stock',
                    'details': response,
                    'total_amount': total_amount
                }, status=200)
            return request.make_json_response({
                'status': 'sufficient_stock',
                'details': response['sufficient_stock'],
                'total_amount': total_amount
            }, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop", type="http", auth="public", methods=["GET"], csrf=False)
    def shop_list(self, **kw):
        try:
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', 20)), 100)
            offset = (page - 1) * limit
            stores_sudo = request.env['res.partner'].sudo()
            total = stores_sudo.search_count([('type', '=', 'store')])
            pages = (total + limit - 1) // limit
            page = min(max(1, page), pages) if pages > 0 else 1
            stores = stores_sudo.search(
                [('type', '=', 'store')],
                offset=offset,
                limit=limit,
                order='id'
            )
            shops_data = [{
                'id': shop.id,
                'name': shop.name or '',
                'phoneNumber': self._string_to_string_list(shop.phone) or [],
                "address": [shop.customer_address] if shop.customer_address else [],
                'wifi': self._string_to_string_list(shop.wifi_name) or [],
                'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids]
            } for shop in stores]
            resp = {
                'shops': shops_data,
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': pages
                }
            }
            return Response(json.dumps(resp), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="public", methods=["GET"], csrf=False)
    def shop_detail(self, shop_id, **kw):
        try:
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            resp = {
                'id': shop.id,
                'name': shop.name or '',
                'phoneNumber': self._string_to_string_list(shop.phone) or [],
                "address": [shop.customer_address] if shop.customer_address else [],
                'wifi': self._string_to_string_list(shop.wifi_name) or [],
                'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids]
            }
            return Response(json.dumps(resp), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop", type="http", auth="angkit", methods=["POST"], csrf=False)
    def shop_create(self, **kw):
        try:
            data = request.httprequest.form
            create_data = {k: v for k, v in data.items() if k in PARTNER_FIELDS}
            if not all(field in create_data for field in ['name', 'phone', 'wifi_name', 'customer_address']):
                return Response(json.dumps({'error': 'Missing required fields'}), status=400, content_type='application/json')
            shop = request.env['res.partner'].sudo().with_context(create_company=True).create([create_data])
            if shop:
                request.env.user.partner_id.update({'parent_id': shop.id})
            resp = {'id': shop.id, 'name': shop.name}
            return Response(json.dumps(resp), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def shop_update(self, shop_id, **kw):
        try:
            data = request.httprequest.form
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': f'Shop with ID {shop_id} not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in PARTNER_FIELDS}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            shop.write(update_fields)
            return Response(json.dumps({'message': f'Shop with ID {shop_id} updated successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", methods=["PATCH"], csrf=False)
    def shop_patch(self, shop_id, **kw):
        try:
            data = request.httprequest.form
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': f'Shop with ID {shop_id} not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in PARTNER_FIELDS}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            shop.write(update_fields)
            return Response(json.dumps({'message': f'Shop with ID {shop_id} patched successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", methods=["DELETE"], csrf=False)
    def shop_delete(self, shop_id, **kw):
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': f'Shop with ID {shop_id} not found'}), status=404, content_type='application/json')
            shop.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="public", methods=["GET"], csrf=False)
    def product_list(self, shop_id, **kw):
        try:
            products = request.env['product.product'].sudo().search([('shop_id', '=', shop_id)])
            data = []
            for product in products:
                tmp_data = self._product_to_dict(product)
                tmp_data['options'] = [self._get_product_options(option) for option in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'radio')]
                tmp_data['choices'] = [self._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'multi')]
                data.append(tmp_data)
            return Response(json.dumps(data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="public", methods=["GET"], csrf=False)
    def product_detail(self, shop_id, product_id, **kw):
        try:
            product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
            if not product:
                return Response(json.dumps({'error': 'Product not found'}), status=404, content_type='application/json')
            response = self._get_product_details(product)
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="angkit", methods=["POST"], csrf=False)
    def product_create(self, shop_id, **kw):
        try:
            data = request.httprequest.form
            image_file = request.httprequest.files.get('image')
            required_fields = ['name', 'price', 'category_id']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return Response(json.dumps({'error': f'Missing required fields: {", ".join(missing_fields)}'}), status=400, content_type='application/json')
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': f'Shop with ID {shop_id} not found'}), status=404, content_type='application/json')
            category = request.env['product.category'].sudo().search([('id', '=', data.get('category_id'))], limit=1)
            if not category:
                return Response(json.dumps({'error': f'Category with ID {data.get("category_id")} not found'}), status=404, content_type='application/json')
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
            product = request.env['product.product'].with_user(request.env.user).create(product_data)
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                product.write({'image_1920': encoded_image})
            # (Attributes/values logic omitted for brevity, can be added as needed)
            resp = {
                'id': product.id,
                'name': product.name,
                'price': product.list_price,
                'category_id': product.categ_id.id
            }
            return Response(json.dumps(resp), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def product_update(self, shop_id, product_id, **kw):
        try:
            data = request.httprequest.form
            image_file = request.httprequest.files.get('image')
            product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
            if not product:
                return Response(json.dumps({'error': f'Product with ID {product_id} not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'list_price', 'categ_id', 'description', 'barcode', 'qty_available']}
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                update_fields['image_1920'] = encoded_image
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            product.write(update_fields)
            return Response(json.dumps({'message': f'Product with ID {product_id} updated successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="angkit", methods=["PATCH"], csrf=False)
    def product_patch(self, shop_id, product_id, **kw):
        try:
            data = request.httprequest.form
            image_file = request.httprequest.files.get('image')
            product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
            if not product:
                return Response(json.dumps({'error': f'Product with ID {product_id} not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'list_price', 'categ_id', 'description', 'barcode', 'qty_available']}
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                update_fields['image_1920'] = encoded_image
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            product.write(update_fields)
            return Response(json.dumps({'message': f'Product with ID {product_id} patched successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="angkit", methods=["DELETE"], csrf=False)
    def product_delete(self, shop_id, product_id, **kw):
        try:
            product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
            if not product:
                return Response(json.dumps({'error': f'Product with ID {product_id} not found'}), status=404, content_type='application/json')
            product.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", type="http", auth="public", methods=["GET"], csrf=False)
    def category_list(self, shop_id, **kw):
        try:
            categories = request.env['product.category'].sudo().search([('shop_id', '=', shop_id)])
            data = [self._category_to_dict(cate) for cate in categories]
            return Response(json.dumps(data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", type="http", auth="angkit", methods=["POST"], csrf=False)
    def category_create(self, shop_id, **kw):
        try:
            data = request.httprequest.form
            if 'name' not in data:
                return Response(json.dumps({'error': 'Category name is required'}), status=400, content_type='application/json')
            category = request.env['product.category'].with_user(request.env.user).create({
                'name': data['name'],
                'shop_id': shop_id,
            })
            return Response(json.dumps(self._category_to_dict(category)), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def category_update(self, shop_id, cate_id, **kw):
        try:
            data = request.httprequest.form
            category = request.env['product.category'].with_user(request.env.user).search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if not category:
                return Response(json.dumps({'error': f'Category with ID {cate_id} not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'shop_id']}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            category.write(update_fields)
            return Response(json.dumps(self._category_to_dict(category)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["PATCH"], csrf=False)
    def category_patch(self, shop_id, cate_id, **kw):
        try:
            data = request.httprequest.form
            category = request.env['product.category'].with_user(request.env.user).search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if not category:
                return Response(json.dumps({'error': f'Category with ID {cate_id} not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'shop_id']}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            category.write(update_fields)
            return Response(json.dumps(self._category_to_dict(category)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["DELETE"], csrf=False)
    def category_delete(self, shop_id, cate_id, **kw):
        try:
            category = request.env['product.category'].with_user(request.env.user).search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if not category:
                return Response(json.dumps({'error': f'Category with ID {cate_id} not found'}), status=404, content_type='application/json')
            category.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    def _build_product_variants_data(self, data, shop_id):
        return {
            'create_variant': data.get('create_variant'),
            'display_type': data.get('display_type'),
            'name': data.get('name'),
            'shop_id': shop_id
        }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["GET"], csrf=False)
    def variant_list(self, shop_id, **kw):
        try:
            attributes = request.env['product.attribute'].sudo().search([
                ('create_uid', '=', request.env.user.id),
                ('shop_id', '=', shop_id)
            ])
            data = [self._attribute_to_dict(attribute) for attribute in attributes]
            return Response(json.dumps(data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["POST"], csrf=False)
    def variant_create(self, shop_id, **kw):
        try:
            data = request.httprequest.form
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}
            REQUIRED_FIELDS = {'create_variant', 'display_type', 'name'}
            missing_fields = REQUIRED_FIELDS - set(data.keys())
            if missing_fields:
                return Response(json.dumps({'error': f'Missing required fields: {", ".join(missing_fields)}'}), status=400, content_type='application/json')
            if data['create_variant'] not in VALID_CREATE_VARIANTS:
                return Response(json.dumps({'error': f'Invalid create_variant value. Must be one of: {", ".join(VALID_CREATE_VARIANTS)}'}), status=400, content_type='application/json')
            if data['display_type'] not in VALID_DISPLAY_TYPES:
                return Response(json.dumps({'error': f'Invalid display_type value. Must be one of: {", ".join(VALID_DISPLAY_TYPES)}'}), status=400, content_type='application/json')
            if request.env['product.attribute'].sudo().search_count([('name', '=', data['name']), ('shop_id', '=', shop_id)], limit=1):
                return Response(json.dumps({'error': f'Attribute with name {data["name"]} already exists'}), status=400, content_type='application/json')
            variant_create_data = self._build_product_variants_data(data, shop_id)
            if variant_create_data.get('display_type') == 'multi':
                variant_create_data['create_variant'] = 'no_variant'
            attribute = request.env['product.attribute'].sudo().create(variant_create_data)
            return Response(json.dumps(self._attribute_to_dict(attribute)), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def variant_update(self, shop_id, variant_id, **kw):
        try:
            data = request.httprequest.form
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return Response(json.dumps({'error': 'Attribute not found'}), status=404, content_type='application/json')
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}
            if 'create_variant' in data and data['create_variant'] not in VALID_CREATE_VARIANTS:
                return Response(json.dumps({'error': f'Invalid create_variant value. Must be one of: {", ".join(VALID_CREATE_VARIANTS)}'}), status=400, content_type='application/json')
            if 'display_type' in data and data['display_type'] not in VALID_DISPLAY_TYPES:
                return Response(json.dumps({'error': f'Invalid display_type value. Must be one of: {", ".join(VALID_DISPLAY_TYPES)}'}), status=400, content_type='application/json')
            if 'name' in data and data['name'] != attribute.name:
                if request.env['product.attribute'].sudo().search_count([('shop_id', '=', shop_id), ('name', '=', data['name'])], limit=1):
                    return Response(json.dumps({'error': f'Attribute with name {data["name"]} already exists'}), status=400, content_type='application/json')
            if data.get('display_type') == 'multi':
                data['create_variant'] = 'no_variant'
            attribute.write(data)
            return Response(json.dumps(self._attribute_to_dict(attribute)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PATCH"], csrf=False)
    def variant_patch(self, shop_id, variant_id, **kw):
        try:
            data = request.httprequest.form
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return Response(json.dumps({'error': 'Attribute not found'}), status=404, content_type='application/json')
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}
            if 'create_variant' in data and data['create_variant'] not in VALID_CREATE_VARIANTS:
                return Response(json.dumps({'error': f'Invalid create_variant value. Must be one of: {", ".join(VALID_CREATE_VARIANTS)}'}), status=400, content_type='application/json')
            if 'display_type' in data and data['display_type'] not in VALID_DISPLAY_TYPES:
                return Response(json.dumps({'error': f'Invalid display_type value. Must be one of: {", ".join(VALID_DISPLAY_TYPES)}'}), status=400, content_type='application/json')
            if 'name' in data and data['name'] != attribute.name:
                if request.env['product.attribute'].sudo().search_count([('shop_id', '=', shop_id), ('name', '=', data['name'])], limit=1):
                    return Response(json.dumps({'error': f'Attribute with name {data["name"]} already exists'}), status=400, content_type='application/json')
            if data.get('display_type') == 'multi':
                data['create_variant'] = 'no_variant'
            attribute.write(data)
            return Response(json.dumps(self._attribute_to_dict(attribute)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["DELETE"], csrf=False)
    def variant_delete(self, shop_id, variant_id, **kw):
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', variant_id),
                ('shop_id', '=', shop_id),
                ('create_uid', '=', request.env.user.id)
            ], limit=1)
            if not attribute:
                return Response(json.dumps({'error': 'Attribute not found'}), status=404, content_type='application/json')
            attribute.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/calculate-price", auth="public", type="http",
                cors="*")
    def calculate_product_price(self, shop_id, product_id):
        """
        Calculate the total price of a product including its variants.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/{product_id}/calculate-price
        Auth: Public
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the product
            product_id (int): The ID of the product to calculate price for

        Request Body:
            {
                "quantity": int,           # Required: Quantity of the product
                "variants": [              # Optional: List of selected variants
                    {
                        "attribute_id": int,    # Required: ID of the attribute
                        "value_id": int         # Required: ID of the selected value
                    },
                    ...
                ]
            }

        Returns:
            dict: Response containing calculated price details
                {
                    'status': str,         # 'success' or 'error'
                    'message': str,        # Success or error message
                    'price_details': {     # Only present on success
                        'base_price': float,    # Original product price
                        'variant_prices': [     # List of variant prices
                            {
                                'attribute_name': str,
                                'value_name': str,
                                'price': float
                            }
                        ],
                        'total_variant_price': float,  # Sum of all variant prices
                        'quantity': int,               # Requested quantity
                        'subtotal': float,            # Base price * quantity
                        'total': float                # Final total with variants
                    }
                }

        Status Codes:
            200: Price calculated successfully
            400: Invalid request data
            404: Product or variant not found
            500: Internal server error

        Example Request:
            {
                "quantity": 2,
                "variants": [
                    {
                        "attribute_id": 1,
                        "value_id": 2
                    },
                    {
                        "attribute_id": 2,
                        "value_id": 3
                    }
                ]
            }

        Example Response (Success):
            {
                "status": "success",
                "price_details": {
                    "base_price": 99.99,
                    "variant_prices": [
                        {
                            "attribute_name": "Size",
                            "value_name": "Large",
                            "price": 5.00
                        },
                        {
                            "attribute_name": "Toppings",
                            "value_name": "Extra Cheese",
                            "price": 2.50
                        }
                    ],
                    "total_variant_price": 7.50,
                    "quantity": 2,
                    "subtotal": 199.98,
                    "total": 214.98
                }
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Product not found"
            }
        """
        try:
            data = request.get_json_data()

            # Validate required fields
            if 'quantity' not in data:
                return {
                    'status': 'error',
                    'message': 'Quantity is required'
                }

            # Validate quantity is positive
            quantity = int(data['quantity'])
            if quantity <= 0:
                return {
                    'status': 'error',
                    'message': 'Quantity must be greater than 0'
                }

            # Get product
            product = request.env['product.product'].sudo().search([
                ('id', '=', product_id),
                ('shop_id', '=', shop_id)
            ], limit=1)

            if not product:
                return {
                    'status': 'error',
                    'message': 'Product not found'
                }

            # Initialize price details
            base_price = product.list_price
            variant_prices = []
            total_variant_price = 0.0

            # Calculate variant prices if provided
            if 'variants' in data and isinstance(data['variants'], list):
                for variant in data['variants']:
                    if not all(k in variant for k in ['attribute_id', 'value_id']):
                        continue

                    # Get attribute and value
                    attribute = request.env['product.attribute'].sudo().browse(variant['attribute_id'])
                    value = request.env['product.attribute.value'].sudo().browse(variant['value_id'])

                    if not attribute.exists() or not value.exists():
                        continue

                    # Add variant price
                    variant_price = value.price_extra
                    variant_prices.append({
                        'attribute_name': attribute.name,
                        'value_name': value.name,
                        'price': variant_price
                    })
                    total_variant_price += variant_price

            # Calculate totals
            subtotal = base_price * quantity
            total = (base_price + total_variant_price) * quantity

            return {
                'status': 'success',
                'price_details': {
                    'base_price': base_price,
                    'variant_prices': variant_prices,
                    'total_variant_price': total_variant_price,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'total': total
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error calculating price: {str(e)}'
            }

    def _attribute_to_dict(self, attribute):
        try:
            return {
                'id': attribute.id,
                'name': attribute.name,
                'create_variant': attribute.create_variant,
                'display_type': attribute.display_type,
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error converting attribute to dictionary: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>/value", type="http", auth="angkit", methods=["GET"], csrf=False)
    def variant_value_list(self, shop_id, variant_id, **kw):
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return Response(json.dumps({'error': 'Attribute not found'}), status=404, content_type='application/json')
            value_list = [{
                'id': value.id,
                'name': value.name,
                'extra_price': value.price_extra
            } for value in attribute.value_ids]
            return Response(json.dumps({'values': value_list}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value", type="http", auth="angkit", methods=["POST"], csrf=False)
    def variant_value_create(self, shop_id, **kw):
        try:
            data = request.httprequest.form
            if 'attribute_id' not in data or 'values' not in data:
                return Response(json.dumps({'error': 'Missing required fields: attribute_id, values'}), status=400, content_type='application/json')
            attribute = request.env['product.attribute'].sudo().browse(int(data['attribute_id']))
            if not attribute.exists():
                return Response(json.dumps({'error': f'Attribute with ID {data["attribute_id"]} not found'}), status=404, content_type='application/json')
            if attribute.shop_id.id != shop_id:
                return Response(json.dumps({'error': "Attribute doesn't belong to this shop"}), status=400, content_type='application/json')
            try:
                values_data = json.loads(data['values'])
                if not isinstance(values_data, list):
                    return Response(json.dumps({'error': 'Values must be a list'}), status=400, content_type='application/json')
                values_to_create = [{
                    'default_extra_price': value.get('extra_price', 0.0),
                    'name': value['name'],
                    'attribute_id': attribute.id,
                } for value in values_data if 'name' in value]
                request.env['product.attribute.value'].sudo().create(values_to_create)
                return Response(json.dumps({'message': 'Attribute values created successfully'}), status=201, content_type='application/json')
            except json.JSONDecodeError:
                return Response(json.dumps({'error': 'Invalid JSON format for values'}), status=400, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def variant_value_update(self, shop_id, value_id, **kw):
        try:
            data = request.httprequest.form
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return Response(json.dumps({'error': 'Variant value not found'}), status=404, content_type='application/json')
            if variant_value.create_uid.id != request.env.user.id:
                return Response(json.dumps({'error': 'You are not authorized to update this variant value'}), status=403, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'price_extra']}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            variant_value.write(update_fields)
            return Response(json.dumps({'message': 'Variant value updated successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["PATCH"], csrf=False)
    def variant_value_patch(self, shop_id, value_id, **kw):
        try:
            data = request.httprequest.form
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return Response(json.dumps({'error': 'Variant value not found'}), status=404, content_type='application/json')
            if variant_value.create_uid.id != request.env.user.id:
                return Response(json.dumps({'error': 'You are not authorized to update this variant value'}), status=403, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'price_extra']}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            variant_value.write(update_fields)
            return Response(json.dumps({'message': 'Variant value patched successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["DELETE"], csrf=False)
    def variant_value_delete(self, shop_id, value_id, **kw):
        try:
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return Response(json.dumps({'error': 'Variant value not found'}), status=404, content_type='application/json')
            if variant_value.create_uid.id != request.env.user.id:
                return Response(json.dumps({'error': 'You are not authorized to delete this variant value'}), status=403, content_type='application/json')
            variant_value.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
