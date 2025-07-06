import base64
import json
import re
import uuid
from datetime import timedelta
import requests
from odoo import http, Command, fields, _
from odoo.http import request, Response
from odoo.tools import config
from collections import defaultdict
from werkzeug.exceptions import NotFound, BadRequest
from functools import wraps
from typing import List

# Additional constants from controllers.py
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_TIMEOUT = 10

SALE_STATE = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'sale': 'Sale Order',
    'cancel': 'Cancelled'
}

# Utility decorators from controllers.py
def validate_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if not request.env.user or request.env.user.id == request.env.ref('base.public_user').id:
                return request.make_json_response({'error': 'Authentication required'}, status=401)
            return func(*args, **kwargs)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)
    return wrapper

def validate_input_data(required_fields: List[str] = None, optional_fields: List[str] = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                    data = request.get_json_data()
                else:
                    data = dict(request.params)
                if not data:
                    return request.make_json_response({'error': 'No data provided'}, status=400)
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return request.make_json_response({'error': f'Missing required fields: {", ".join(missing_fields)}'}, status=400)
                if optional_fields:
                    all_valid_fields = set(required_fields or []) | set(optional_fields or [])
                    invalid_fields = [field for field in data.keys() if field not in all_valid_fields]
                    if invalid_fields:
                        return request.make_json_response({'error': f'Invalid fields: {", ".join(invalid_fields)}'}, status=400)
                return func(*args, **kwargs)
            except Exception as e:
                return request.make_json_response({'error': str(e)}, status=500)
        return wrapper
    return decorator

def paginate_results(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            page = int(request.params.get('page', 1))
            limit = min(int(request.params.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            if page < 1:
                return request.make_json_response({'error': 'Page number must be positive'}, status=400)
            kwargs['page'] = page
            kwargs['limit'] = limit
            kwargs['offset'] = (page - 1) * limit
            return func(*args, **kwargs)
        except ValueError:
            return request.make_json_response({'error': 'Invalid pagination parameters'}, status=400)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)
    return wrapper

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
    """
    RESTful API controller for the Angkort shop system.

    This controller manages endpoints for:
    - Products and product variants
    - Product categories
    - Shops (list, detail, create, update, delete)
    - Orders (customer orders, cart checkout)
    - Miscellaneous endpoints (industries, login, etc.)

    All endpoints follow RESTful conventions and return JSON responses.
    """

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

    def _generate_token(self, user_id, token_type, minutes=0, days=0):
        """
        Generate a JWT token for the user.
        
        Args:
            user_id (int): User ID
            token_type (str): Type of token ('access' or 'refresh')
            minutes (int): Token expiry in minutes
            days (int): Token expiry in days
            
        Returns:
            str: Generated JWT token
        """
        import jwt
        from datetime import datetime, timedelta
        
        # Calculate expiry time
        expiry = datetime.utcnow()
        if days > 0:
            expiry += timedelta(days=days)
        if minutes > 0:
            expiry += timedelta(minutes=minutes)
        
        # Create payload
        payload = {
            'user_id': user_id,
            'token_type': token_type,
            'exp': expiry,
            'iat': datetime.utcnow()
        }
        
        # Generate token (you should use a secret key from config)
        secret_key = 'your-secret-key-here'  # Replace with actual secret key
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        return token

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

    # --- ORDER ROUTES ---
    @http.route(f"{BASE_URL}/my/order", csrf=False, auth="angkit", type="http", methods=["GET"], cors="*")
    def my_order(self, **kwargs):
        """
        Retrieve paginated list of orders for the authenticated user.

        Route: GET /angkort/api/v1/my/order

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of user orders grouped by state.
            500: On server error.

        Example Response:
            {
                "orders": {
                    "draft": [
                        {
                            "id": 1,
                            "name": "SO001",
                            "date_order": "01-01-2024",
                            "total": 100.0,
                            "state": "Quotation"
                        }
                    ]
                },
                "pagination": {
                    "total": 10,
                    "page": 1,
                    "limit": 20,
                    "pages": 1
                }
            }
        """
        try:
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', 20)), 100)
            offset = (page - 1) * limit
            domain = [('partner_id', '=', request.env.user.partner_id.id)]
            total = request.env['sale.order'].sudo().search_count(domain)
            pages = (total + limit - 1) // limit
            page = min(max(1, page), pages) if pages > 0 else 1
            sales = request.env['sale.order'].sudo().search(
                domain,
                offset=offset,
                limit=limit,
                order='date_order desc'
            )
            sales_data = sales.read(['id', 'name', 'date_order', 'amount_total', 'state'])
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

    @http.route(f'{BASE_URL}/my/order/<int:order_id>', csrf=False, auth="angkit", type="http", methods=["GET"], cors="*")
    def my_order_detail(self, order_id, **kwargs):
        """
        Retrieve detailed information for a specific order.

        Route: GET /angkort/api/v1/my/order/<order_id>

        Parameters:
            order_id (int): The ID of the order.

        Returns:
            200: Detailed order information with order lines.
            404: If the order is not found.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "partner_id": 1,
                "partner_name": "Customer A",
                "delivery_address": "123 Main St",
                "name": "SO001",
                "date_order": "01-01-2024",
                "total": 100.0,
                "state": "Quotation",
                "order_lines": [...]
            }
        """
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

    @http.route(f"{BASE_URL}/cart/checkout", csrf=False, auth="angkit", type="json", methods=["POST"], cors="*")
    def cart_checkout(self):
        """
        Validate cart items and check stock availability.

        Route: POST /angkort/api/v1/cart/checkout

        Parameters (JSON body):
            cart (list): List of cart items, each containing:
                - product_id (int): Product ID
                - quantity (int): Quantity to order

        Returns:
            200: Cart validation results with stock status.
            400: If cart is invalid or empty.
            500: On server error.

        Example Response:
            {
                "status": "insufficient_stock",
                "details": {
                    "sufficient_stock": [...],
                    "insufficient_stock": [...]
                },
                "total_amount": 150.0
            }
        """
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

    # --- SHOP ROUTES ---
    @http.route(f"{BASE_URL}/shop", type="http", auth="public", methods=["GET"], csrf=False)
    def shop_list(self, **kw):
        """
        Retrieve a paginated list of all shops.

        Route: GET /angkort/api/v1/shop

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of shops with pagination metadata.
            500: On server error.

        Example Response:
            {
                "shops": [
                    {
                        "id": 1,
                        "name": "Shop A",
                        "phoneNumber": ["123456789"],
                        "address": ["123 Main St"],
                        "wifi": ["ShopWiFi"],
                        "banks": [...]
                    }
                ],
                "pagination": {
                    "total": 50,
                    "page": 1,
                    "limit": 20,
                    "pages": 3
                }
            }
        """
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
        """
        Retrieve details for a specific shop.

        Route: GET /angkort/api/v1/shop/<shop_id>

        Parameters:
            shop_id (int): The ID of the shop.

        Returns:
            200: Shop details as JSON object.
            404: If the shop is not found.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "name": "Shop A",
                "phoneNumber": ["123456789"],
                "address": ["123 Main St"],
                "wifi": ["ShopWiFi"],
                "banks": [...]
            }
        """
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
        """
        Create a new shop.

        Route: POST /angkort/api/v1/shop

        Parameters (form-data):
            name (str): Shop name (required).
            phone (str): Phone number (required).
            customer_address (str): Shop address (required).
            wifi_name (str, optional): WiFi network name.
            shop_latitude (float, optional): Shop latitude.
            shop_longitude (float, optional): Shop longitude.
            email (str, optional): Shop email.

        Returns:
            201: Created shop details as JSON object.
            400: If required fields are missing.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "name": "Shop A"
            }
        """
        try:
            data = request.httprequest.form
            create_data = {k: v for k, v in data.items() if k in PARTNER_FIELDS}
            if not all(field in create_data for field in ['name', 'phone', 'customer_address']):
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
        """
        Update an existing shop.

        Route: PUT /angkort/api/v1/shop/<shop_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            (Any updatable shop field)

        Returns:
            200: Success message.
            400: If no valid fields to update.
            404: If the shop is not found.
            500: On server error.
        """
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
        """
        Partially update an existing shop.

        Route: PATCH /angkort/api/v1/shop/<shop_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            (Any updatable shop field)

        Returns:
            200: Success message.
            400: If no valid fields to update.
            404: If the shop is not found.
            500: On server error.
        """
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
        """
        Delete a shop.

        Route: DELETE /angkort/api/v1/shop/<shop_id>

        Parameters:
            shop_id (int): The ID of the shop.

        Returns:
            204: On successful deletion.
            404: If the shop is not found.
            500: On server error.
        """
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': f'Shop with ID {shop_id} not found'}), status=404, content_type='application/json')
            shop.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/create", csrf=False, auth="public", type="http", cors="*", methods=["POST"])
    def create_shop(self, **kw):
        """
        Create a new shop (alternative endpoint).

        Route: POST /angkort/api/v1/shop/create

        Parameters (JSON or form-data):
            name (str): Shop name (required).
            phone (str): Phone number (required).
            customer_address (str): Shop address (required).
            wifi_name (str, optional): WiFi network name.
            shop_latitude (float, optional): Shop latitude.
            shop_longitude (float, optional): Shop longitude.
            email (str, optional): Shop email.

        Returns:
            201: Created shop details with success message.
            400: If required fields are missing.
            500: On server error.

        Example Response:
            {
                "status": true,
                "data": {
                    "name": "Shop A",
                    "id": 1
                },
                "message": "Shop created successfully"
            }
        """
        try:
            data = self._get_request_data() if hasattr(self, '_get_request_data') else (request.get_json_data() if request.httprequest.content_type and 'application/json' in request.httprequest.content_type else dict(request.params))
            create_data = data.get('params', data)
            required_fields = ['name', 'phone', 'customer_address']
            missing_fields = [field for field in required_fields if not create_data.get(field)]
            if missing_fields:
                return request.make_json_response({'status': False, 'message': f"Missing required fields: {', '.join(missing_fields)}"}, status=400)
            shop_data = request.env['res.partner'].sudo().with_context(create_company=True).create([{
                'name': create_data['name'],
                'phone': create_data['phone'],
                'customer_address': create_data['customer_address'],
                'type': 'store',
                'wifi_name': create_data.get('wifi_name', ''),
                'shop_latitude': create_data.get('shop_latitude', 0.0),
                'shop_longitude': create_data.get('shop_longitude', 0.0),
                'email': create_data.get('email', ''),
            }])
            if request.env.user.id != request.env.ref('base.public_user').id:
                request.env.user.partner_id.update({'parent_id': shop_data.id})
            return request.make_json_response({'status': True, 'data': {'name': shop_data.name, 'id': shop_data.id}, 'message': 'Shop created successfully'}, status=201)
        except Exception as e:
            return request.make_json_response({'status': False, 'message': f'Error creating shop: {str(e)}'}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="public", methods=["GET"], csrf=False)
    def product_list(self, shop_id, **kw):
        """
        Retrieve all products for a given shop.

        Route: GET /angkort/api/v1/shop/<shop_id>/product

        Parameters:
            shop_id (int): The ID of the shop.

        Returns:
            200: List of products with their details.
            404: If the shop is not found.
            500: On server error.

        Example Response:
            [
                {
                    "id": 1,
                    "name": "Product A",
                    ...
                },
                ...
            ]
        """
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
        """
        Retrieve details for a specific product in a shop.

        Route: GET /angkort/api/v1/shop/<shop_id>/product/<product_id>

        Parameters:
            shop_id (int): The ID of the shop.
            product_id (int): The ID of the product.

        Returns:
            200: Product details as a JSON object.
            404: If the product is not found.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "name": "Product A",
                ...
            }
        """
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
        """
        Create a new product for a given shop.

        Route: POST /angkort/api/v1/shop/<shop_id>/product

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            name (str): Name of the product (required).
            price (float): Price of the product (required).
            category_id (int): Category ID (required).
            description (str, optional): Product description.
            barcode (str, optional): Product barcode.
            qty_available (float, optional): Initial stock quantity.
            image (file, optional): Product image.

        Returns:
            201: Created product details as a JSON object.
            400: If required fields are missing.
            404: If the shop or category is not found.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "name": "Product A",
                "price": 10.0,
                "category_id": 2
            }
        """
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
        """
        Update an existing product in a shop.

        Route: PUT /angkort/api/v1/shop/<shop_id>/product/<product_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            product_id (int): The ID of the product.
            name (str, optional): New name.
            list_price (float, optional): New price.
            categ_id (int, optional): New category ID.
            description (str, optional): New description.
            barcode (str, optional): New barcode.
            qty_available (float, optional): New stock quantity.
            image (file, optional): New product image.

        Returns:
            200: Success message.
            400: If no valid fields to update.
            404: If the product is not found.
            500: On server error.
        """
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
        """
        Partially update an existing product in a shop.

        Route: PATCH /angkort/api/v1/shop/<shop_id>/product/<product_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            product_id (int): The ID of the product.
            (Any updatable product field)

        Returns:
            200: Success message.
            400: If no valid fields to update.
            404: If the product is not found.
            500: On server error.
        """
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
        """
        Delete a product from a shop.

        Route: DELETE /angkort/api/v1/shop/<shop_id>/product/<product_id>

        Parameters:
            shop_id (int): The ID of the shop.
            product_id (int): The ID of the product.

        Returns:
            204: On successful deletion.
            404: If the product is not found.
            500: On server error.
        """
        try:
            product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
            if not product:
                return Response(json.dumps({'error': f'Product with ID {product_id} not found'}), status=404, content_type='application/json')
            product.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/calculate-price", csrf=False, auth="public", type="http", cors="*")
    def calculate_product_price(self, shop_id, product_id):
        """
        Calculate the total price of a product including its variants.

        Route: POST /angkort/api/v1/shop/<shop_id>/product/<product_id>/calculate-price

        Parameters (JSON body):
            quantity (int): Quantity of the product (required).
            variants (list, optional): List of selected variants, each with attribute_id and value_id.

        Returns:
            200: Price calculation details.
            400: If required fields are missing or invalid.
            404: If the product or variant is not found.
            500: On server error.

        Example Response:
            {
                "status": "success",
                "price_details": {
                    "base_price": 99.99,
                    "variant_prices": [...],
                    "total_variant_price": 7.50,
                    "quantity": 2,
                    "subtotal": 199.98,
                    "total": 214.98
                }
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

    @http.route(f"{BASE_URL}/industries", csrf=False, methods=['GET'], auth="public", type="http", cors="*")
    @paginate_results
    def industries(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of all available industries.

        Route: GET /angkort/api/v1/industries

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of industries with pagination metadata.
            500: On server error.

        Example Response:
            {
                "status": true,
                "data": {
                    "industries": [
                        {
                            "id": 1,
                            "full_name": "Information Technology",
                            "name": "IT"
                        }
                    ],
                    "pagination": {
                        "total": 42,
                        "page": 1,
                        "limit": 20,
                        "pages": 3
                    }
                }
            }
        """
        try:
            industries = request.env['res.partner.industry'].sudo().search([], limit=limit, offset=offset, order='name')
            total_count = request.env['res.partner.industry'].sudo().search_count([])
            industries_data = [{
                'id': industry.id,
                'full_name': getattr(industry, 'full_name', industry.name),
                'name': industry.name
            } for industry in industries]
            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
            return request.make_json_response({
                'status': True,
                'data': {
                    'industries': industries_data,
                    'pagination': pagination_data
                }
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error retrieving industries',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/login", auth="public", csrf=False, type="http", cors="*", methods=["POST"])
    def login(self):
        """
        Authenticate user credentials and generate an API access token.

        Route: POST /angkort/api/v1/login

        Parameters (JSON body):
            username (str): User's login name (required).
            password (str): User's password (required).

        Returns:
            200: Authentication success with token and user details.
            400: If required fields are missing.
            401: If authentication fails.
            500: On server error.

        Example Response:
            {
                "status": true,
                "message": "Login successful",
                "data": {
                    "token_key": "a1b2c3d4e5f6",
                    "user_id": 1,
                    "username": "admin"
                }
            }
        """
        try:
            # Get JSON data from request
            if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                data = request.get_json_data()
            else:
                data = dict(request.params)
            
            # Validate required fields
            if not data:
                return request.make_json_response({
                    'status': False,
                    'message': 'No data provided',
                    'error': 'Missing request body'
                }, status=400)
            
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing required fields',
                    'error': 'username and password are required'
                }, status=400)
            
            # Authenticate the user
            user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
            if not user:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Invalid username or password'
                }, status=401)
            
            # Verify password using session authentication
            try:
                db = config['db_name']
                credential = {'login': username, 'password': password, 'type': 'password'}
                uid = request.session.authenticate(db, credential)
                
                if not uid:
                    return request.make_json_response({
                        'status': False,
                        'message': 'Authentication failed',
                        'error': 'Invalid username or password'
                    }, status=401)
                
                # Generate tokens
                access_token = self._generate_token(user.id, 'access', minutes=30)
                refresh_token = self._generate_token(user.id, 'refresh', days=7)
                
                # Store tokens in the database
                token_model = request.env['res.user.token'].sudo()
                token_model.create_token(
                    user_id=user.id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    access_expiry=fields.Datetime.now() + timedelta(minutes=30),
                    refresh_expiry=fields.Datetime.now() + timedelta(days=7)
                )
                
                return request.make_json_response({
                    'status': True,
                    'message': 'Login successful',
                    'data': {
                        'token_key': access_token,
                        'user_id': user.id,
                        'username': user.login
                    }
                }, status=200)
                
            except Exception as auth_error:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': str(auth_error)
                }, status=401)
                
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error during login',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/logout", csrf=False, auth="angkit", type="http", cors="*", methods=["POST"])
    def logout(self):
        """
        Logout user and invalidate their access token.

        Route: POST /angkort/api/v1/logout

        Headers:
            Authorization: Bearer <access_token> (required)

        Returns:
            200: Logout successful.
            401: If authentication fails or token is invalid.
            500: On server error.

        Example Response:
            {
                "status": true,
                "message": "Logout successful"
            }
        """
        try:
            # Get the current user from the authenticated session
            user = request.env.user
            
            if not user or user.id == request.env.ref('base.public_user').id:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication required',
                    'error': 'No valid user session'
                }, status=401)
            
            # Get the authorization header
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid authorization header',
                    'error': 'Bearer token required'
                }, status=401)
            
            # Extract the token
            access_token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Hash the token for database search (same as create_token method)
            import hashlib
            hashed_access_token = hashlib.sha256(access_token.encode()).hexdigest()
            
            # Find and invalidate the token
            token_model = request.env['res.user.token'].sudo()
            token_record = token_model.search([
                ('user_id', '=', user.id),
                ('access_token', '=', hashed_access_token),
                ('active', '=', True)
            ], limit=1)
            
            if token_record:
                # Deactivate the token
                token_record.write({
                    'active': False,
                    'deactivated_at': fields.Datetime.now()
                })
                
                return request.make_json_response({
                    'status': True,
                    'message': 'Logout successful'
                }, status=200)
            else:
                return request.make_json_response({
                    'status': False,
                    'message': 'Token not found',
                    'error': 'Invalid or expired token'
                }, status=401)
                
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error during logout',
                'error': str(e)
            }, status=500)

    # --- CATEGORY ROUTES ---
    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", type="http", auth="public", methods=["GET"], csrf=False)
    def category_list(self, shop_id, **kw):
        """
        Retrieve all product categories for a given shop.

        Route: GET /angkort/api/v1/shop/<shop_id>/product/category

        Parameters:
            shop_id (int): The ID of the shop.

        Returns:
            200: List of categories as JSON array.
            500: On server error.

        Example Response:
            [
                {
                    "id": 1,
                    "name": "Electronics"
                },
                {
                    "id": 2,
                    "name": "Clothing"
                }
            ]
        """
        try:
            categories = request.env['product.category'].sudo().search([('shop_id', '=', shop_id)])
            data = [self._category_to_dict(category) for category in categories]
            return Response(json.dumps(data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", type="http", auth="angkit", methods=["POST"], csrf=False)
    def category_create(self, shop_id, **kw):
        """
        Create a new product category for a given shop.

        Route: POST /angkort/api/v1/shop/<shop_id>/product/category

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            name (str): Name of the category (required).

        Returns:
            201: Created category details as JSON object.
            400: If name is missing.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "name": "Electronics"
            }
        """
        try:
            data = request.httprequest.form
            if 'name' not in data:
                return Response(json.dumps({'error': 'Missing required field: name'}), status=400, content_type='application/json')
            category = request.env['product.category'].sudo().create({
                'name': data['name'],
                'shop_id': shop_id,
            })
            return Response(json.dumps(self._category_to_dict(category)), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def category_update(self, shop_id, cate_id, **kw):
        """
        Update an existing product category in a shop.

        Route: PUT /angkort/api/v1/shop/<shop_id>/product/category/<cate_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            cate_id (int): The ID of the category.
            name (str, optional): New category name.

        Returns:
            200: Updated category details as JSON object.
            400: If no valid fields to update.
            404: If the category is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            category = request.env['product.category'].sudo().search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if not category:
                return Response(json.dumps({'error': 'Category not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name']}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            category.write(update_fields)
            return Response(json.dumps(self._category_to_dict(category)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["PATCH"], csrf=False)
    def category_patch(self, shop_id, cate_id, **kw):
        """
        Partially update an existing product category in a shop.

        Route: PATCH /angkort/api/v1/shop/<shop_id>/product/category/<cate_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            cate_id (int): The ID of the category.
            name (str, optional): New category name.

        Returns:
            200: Updated category details as JSON object.
            400: If no valid fields to update.
            404: If the category is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            category = request.env['product.category'].sudo().search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if not category:
                return Response(json.dumps({'error': 'Category not found'}), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name']}
            if not update_fields:
                return Response(json.dumps({'error': 'No valid fields to update'}), status=400, content_type='application/json')
            category.write(update_fields)
            return Response(json.dumps(self._category_to_dict(category)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["DELETE"], csrf=False)
    def category_delete(self, shop_id, cate_id, **kw):
        """
        Delete a product category from a shop.

        Route: DELETE /angkort/api/v1/shop/<shop_id>/product/category/<cate_id>

        Parameters:
            shop_id (int): The ID of the shop.
            cate_id (int): The ID of the category.

        Returns:
            204: On successful deletion.
            404: If the category is not found.
            500: On server error.
        """
        try:
            category = request.env['product.category'].sudo().search([('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
            if not category:
                return Response(json.dumps({'error': 'Category not found'}), status=404, content_type='application/json')
            category.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    # --- GLOBAL ROUTES (System-wide functionality) ---
    @http.route(f"{BASE_URL}/product/category", csrf=False, methods=['GET'], auth="public", type="http", cors="*")
    @paginate_results
    def global_product_category(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of all product categories (global, not shop-specific).

        Route: GET /angkort/api/v1/product/category

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of all product categories with hierarchical information.
            500: On server error.

        Example Response:
            {
                "status": true,
                "data": {
                    "categories": [
                        {
                            "id": 15,
                            "name": "Electronics",
                            "parent_id": null,
                            "parent_name": null
                        }
                    ],
                    "pagination": {
                        "total": 42,
                        "page": 1,
                        "limit": 20,
                        "pages": 3
                    }
                }
            }
        """
        try:
            categories = request.env['product.category'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )
            total_count = request.env['product.category'].sudo().search_count([])
            categories_data = [{
                'id': category.id,
                'name': category.name,
                'parent_id': category.parent_id.id if category.parent_id else None,
                'parent_name': category.parent_id.name if category.parent_id else None
            } for category in categories]
            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
            return request.make_json_response({
                'status': True,
                'data': {
                    'categories': categories_data,
                    'pagination': pagination_data
                }
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error retrieving product categories',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/image/add", auth="public", type="http", methods=["POST"], csrf=False)
    def image_add(self, quality=0, width=0, height=0, res_id=False, res_model='ir.ui.view', **kw):
        """
        Upload, validate, process, and store an image with automatic WebP conversion.

        Route: POST /angkort/api/v1/image/add

        Parameters:
            quality (int, optional): Image quality percentage (0-100).
            width (int, optional): Target width in pixels.
            height (int, optional): Target height in pixels.
            res_id (int, optional): Related record ID for attachment.
            res_model (str, optional): Related model name for attachment.
            image (file): The image file to upload (required).

        Returns:
            200: Image upload success with URL and ID.
            400: If no image provided or invalid format.
            500: On server error.

        Example Response:
            {
                "status": true,
                "message": "Image uploaded successfully",
                "data": {
                    "image": "/web/image/123/800x600/image.webp",
                    "image_id": 123
                }
            }
        """
        try:
            if 'image' not in request.httprequest.files:
                return request.make_json_response({
                    'status': False,
                    'message': 'No image file provided',
                    'error': 'Missing required file'
                }, status=400)
            
            image_file = request.httprequest.files['image']
            if not image_file.filename:
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid image file',
                    'error': 'Empty file'
                }, status=400)
            
            # Read and encode image
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            data = base64.b64decode(image_data)
            
            # Create attachment
            attachment = request.env['ir.attachment'].sudo().create({
                'name': image_file.filename,
                'datas': data,
                'res_model': res_model,
                'res_id': res_id if res_id else 0,
                'mimetype': image_file.content_type
            })
            
            return request.make_json_response({
                'status': True,
                'message': 'Image uploaded successfully',
                'data': {
                    'image': f'/web/image/{attachment.id}',
                    'image_id': attachment.id
                }
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error uploading image',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/product/<int:product_id>", csrf=False, methods=['GET'], auth="public", type="http", cors="*")
    def global_product_detail(self, product_id):
        """
        Retrieve details for a specific product (global, not shop-specific).

        Route: GET /angkort/api/v1/product/<product_id>

        Parameters:
            product_id (int): The ID of the product.

        Returns:
            200: Product details as JSON object.
            404: If the product is not found.
            500: On server error.

        Example Response:
            {
                "id": 1,
                "name": "Product A",
                "code": "PROD001",
                "description": "Product description",
                "sale_price": 99.99,
                "image": "base64_image_data",
                "category": {
                    "id": 1,
                    "name": "Electronics"
                }
            }
        """
        try:
            product = request.env['product.product'].sudo().search([('id', '=', product_id)], limit=1)
            if not product:
                return request.make_json_response({
                    'status': False,
                    'message': 'Product not found',
                    'error': 'Product does not exist'
                }, status=404)
            
            product_data = self._product_to_dict(product)
            product_data['options'] = [self._get_product_options(option) for option in product.attribute_line_ids.filtered(
                lambda x: x.attribute_id.display_type == 'radio')]
            product_data['choices'] = [self._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(
                lambda x: x.attribute_id.display_type == 'multi')]
            
            return request.make_json_response({
                'status': True,
                'data': product_data
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error retrieving product',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/product/variant", csrf=False, methods=['GET'], auth="public", type="http", cors="*")
    @paginate_results
    def global_product_variant(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of all product attributes (global, not shop-specific).

        Route: GET /angkort/api/v1/product/variant

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of product attributes.
            500: On server error.

        Example Response:
            {
                "status": true,
                "data": {
                    "attributes": [
                        {
                            "id": 1,
                            "name": "Color",
                            "create_variant": "always",
                            "display_type": "radio"
                        }
                    ],
                    "pagination": {
                        "total": 10,
                        "page": 1,
                        "limit": 20,
                        "pages": 1
                    }
                }
            }
        """
        try:
            attributes = request.env['product.attribute'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )
            total_count = request.env['product.attribute'].sudo().search_count([])
            attributes_data = [self._attribute_to_dict(attribute) for attribute in attributes]
            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
            return request.make_json_response({
                'status': True,
                'data': {
                    'attributes': attributes_data,
                    'pagination': pagination_data
                }
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error retrieving product variants',
                'error': str(e)
            }, status=500)

    @http.route(f'{BASE_URL}/product', csrf=False, methods=['GET'], auth='public', type="http", cors="*")
    @paginate_results
    def global_product_list(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of all products (global, not shop-specific).

        Route: GET /angkort/api/v1/product

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of all products.
            500: On server error.

        Example Response:
            {
                "status": true,
                "data": {
                    "products": [
                        {
                            "id": 1,
                            "name": "Product A",
                            "code": "PROD001",
                            "sale_price": 99.99,
                            "category": {
                                "id": 1,
                                "name": "Electronics"
                            }
                        }
                    ],
                    "pagination": {
                        "total": 100,
                        "page": 1,
                        "limit": 20,
                        "pages": 5
                    }
                }
            }
        """
        try:
            products = request.env['product.product'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )
            total_count = request.env['product.product'].sudo().search_count([])
            products_data = [self._product_to_dict(product) for product in products]
            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
            return request.make_json_response({
                'status': True,
                'data': {
                    'products': products_data,
                    'pagination': pagination_data
                }
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error retrieving products',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/sale", csrf=False, methods=['GET'], auth="public", type="http")
    @paginate_results
    def global_sale_order(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of all sale orders (global, not user-specific).

        Route: GET /angkort/api/v1/sale

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).

        Returns:
            200: Paginated list of all sale orders.
            500: On server error.

        Example Response:
            {
                "status": true,
                "data": {
                    "orders": [
                        {
                            "id": 1,
                            "name": "SO001",
                            "partner_name": "Customer A",
                            "date_order": "2024-01-01",
                            "amount_total": 100.0,
                            "state": "sale"
                        }
                    ],
                    "pagination": {
                        "total": 50,
                        "page": 1,
                        "limit": 20,
                        "pages": 3
                    }
                }
            }
        """
        try:
            orders = request.env['sale.order'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='date_order desc'
            )
            total_count = request.env['sale.order'].sudo().search_count([])
            orders_data = [{
                'id': order.id,
                'name': order.name,
                'partner_name': order.partner_id.name,
                'date_order': order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
                'amount_total': order.amount_total,
                'state': order.state
            } for order in orders]
            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
            return request.make_json_response({
                'status': True,
                'data': {
                    'orders': orders_data,
                    'pagination': pagination_data
                }
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error retrieving sale orders',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/order", csrf=False, auth="public", type="http", methods=["POST"], cors="*")
    def global_new_order(self):
        """
        Create a new sale order (global order creation).

        Route: POST /angkort/api/v1/order

        Parameters (JSON body):
            partner_id (int): Customer ID (required).
            order_lines (list): List of order line items, each containing:
                - product_id (int): Product ID (required).
                - quantity (float): Quantity (required).
                - price_unit (float, optional): Unit price.

        Returns:
            201: Created order details.
            400: If required fields are missing.
            500: On server error.

        Example Response:
            {
                "status": true,
                "message": "Order created successfully",
                "data": {
                    "order_id": 1,
                    "order_name": "SO001"
                }
            }
        """
        try:
            data = request.get_json_data()
            if not data:
                return request.make_json_response({
                    'status': False,
                    'message': 'No data provided',
                    'error': 'Missing request body'
                }, status=400)
            
            if 'partner_id' not in data or 'order_lines' not in data:
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing required fields',
                    'error': 'partner_id and order_lines are required'
                }, status=400)
            
            # Create order lines
            order_lines = []
            for line in data['order_lines']:
                if 'product_id' not in line or 'quantity' not in line:
                    continue
                order_line = Command.create({
                    'product_id': line['product_id'],
                    'product_uom_qty': line['quantity'],
                    'price_unit': line.get('price_unit', 0.0)
                })
                order_lines.append(order_line)
            
            if not order_lines:
                return request.make_json_response({
                    'status': False,
                    'message': 'No valid order lines',
                    'error': 'At least one valid order line is required'
                }, status=400)
            
            # Create sale order
            order = request.env['sale.order'].sudo().create({
                'partner_id': data['partner_id'],
                'order_line': order_lines
            })
            
            return request.make_json_response({
                'status': True,
                'message': 'Order created successfully',
                'data': {
                    'order_id': order.id,
                    'order_name': order.name
                }
            }, status=201)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error creating order',
                'error': str(e)
            }, status=500)

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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:variant_id>/value", type="http", auth="angkit", methods=["GET"], csrf=False)
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

    # --- SHOP-SPECIFIC PRODUCT VARIANT ROUTES ---
    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["GET"], csrf=False)
    def variant_list(self, shop_id, **kw):
        """
        Retrieve all product variants for a specific shop.

        Route: GET /angkort/api/v1/shop/<shop_id>/product/variant

        Parameters:
            shop_id (int): The ID of the shop.

        Returns:
            200: List of product variants for the shop.
            500: On server error.
        """
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
        """
        Create a new product variant for a specific shop.

        Route: POST /angkort/api/v1/shop/<shop_id>/product/variant

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            name (str): Variant name (required).
            create_variant (str): Variant creation type (required).
            display_type (str): Display type (required).

        Returns:
            201: Created variant details.
            400: If required fields are missing.
            500: On server error.
        """
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
            variant_create_data = {
                'name': data['name'],
                'create_variant': data['create_variant'],
                'display_type': data['display_type'],
                'shop_id': shop_id
            }
            if variant_create_data.get('display_type') == 'multi':
                variant_create_data['create_variant'] = 'no_variant'
            attribute = request.env['product.attribute'].sudo().create(variant_create_data)
            return Response(json.dumps(self._attribute_to_dict(attribute)), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PUT"], csrf=False)
    def variant_update(self, shop_id, variant_id, **kw):
        """
        Update an existing product variant for a specific shop.

        Route: PUT /angkort/api/v1/shop/<shop_id>/product/variant/<variant_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            variant_id (int): The ID of the variant.
            name (str, optional): New variant name.
            create_variant (str, optional): New variant creation type.
            display_type (str, optional): New display type.

        Returns:
            200: Updated variant details.
            400: If no valid fields to update.
            404: If the variant is not found.
            500: On server error.
        """
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
        """
        Partially update an existing product variant for a specific shop.

        Route: PATCH /angkort/api/v1/shop/<shop_id>/product/variant/<variant_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            variant_id (int): The ID of the variant.
            (Any updatable variant field)

        Returns:
            200: Updated variant details.
            400: If no valid fields to update.
            404: If the variant is not found.
            500: On server error.
        """
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
        """
        Delete a product variant from a specific shop.

        Route: DELETE /angkort/api/v1/shop/<shop_id>/product/variant/<variant_id>

        Parameters:
            shop_id (int): The ID of the shop.
            variant_id (int): The ID of the variant.

        Returns:
            204: On successful deletion.
            404: If the variant is not found.
            500: On server error.
        """
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
