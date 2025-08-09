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


def verify_ownership(entity_type='shop'):
    """
    Decorator to verify that the current user owns the entity they're trying to modify.
    
    Args:
        entity_type (str): Type of entity to check ('shop', 'product', 'category', 'variant', 'variant_value', 'wifi', 'open_hour')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                current_user_id = request.env.user.id
                
                if entity_type == 'shop':
                    shop_id = kwargs.get('shop_id')
                    if not shop_id:
                        return request.make_json_response({'error': 'Shop ID is required'}, status=400)
                    
                    shop = request.env['res.partner'].sudo().search([
                        ('id', '=', shop_id),
                        ('type', '=', 'store')
                    ], limit=1)
                    
                    if not shop:
                        return request.make_json_response({'error': 'Shop not found'}, status=404)
                    
                    if shop.create_uid.id != current_user_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only modify shops you own'
                        }, status=403)
                
                elif entity_type == 'product':
                    shop_id = kwargs.get('shop_id')
                    product_id = kwargs.get('product_id')
                    
                    if not shop_id or not product_id:
                        return request.make_json_response({'error': 'Shop ID and Product ID are required'}, status=400)
                    
                    product = request.env['product.template'].sudo().search([
                        ('id', '=', product_id),
                        ('shop_id', '=', shop_id)
                    ], limit=1)
                    
                    if not product:
                        return request.make_json_response({'error': 'Product not found'}, status=404)
                    
                    if product.create_uid.id != current_user_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only modify products you own'
                        }, status=403)
                
                elif entity_type == 'category':
                    shop_id = kwargs.get('shop_id')
                    cate_id = kwargs.get('cate_id')
                    
                    if not shop_id or not cate_id:
                        return request.make_json_response({'error': 'Shop ID and Category ID are required'}, status=400)
                    
                    category = request.env['product.category'].sudo().search([
                        ('id', '=', cate_id),
                        ('shop_id', '=', shop_id)
                    ], limit=1)
                    
                    if not category:
                        return request.make_json_response({'error': 'Category not found'}, status=404)
                    
                    if category.create_uid.id != current_user_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only modify categories you own'
                        }, status=403)
                
                elif entity_type == 'variant':
                    shop_id = kwargs.get('shop_id')
                    variant_id = kwargs.get('variant_id')
                    
                    if not shop_id or not variant_id:
                        return request.make_json_response({'error': 'Shop ID and Variant ID are required'}, status=400)
                    
                    variant = request.env['product.attribute'].sudo().search([
                        ('id', '=', variant_id),
                        ('shop_id', '=', shop_id)
                    ], limit=1)
                    
                    if not variant:
                        return request.make_json_response({'error': 'Variant not found'}, status=404)
                    
                    if variant.create_uid.id != current_user_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only modify variants you own'
                        }, status=403)
                
                elif entity_type == 'variant_value':
                    shop_id = kwargs.get('shop_id')
                    value_id = kwargs.get('value_id')
                    
                    if not shop_id or not value_id:
                        return request.make_json_response({'error': 'Shop ID and Value ID are required'}, status=400)
                    
                    variant_value = request.env['product.attribute.value'].sudo().search([
                        ('id', '=', value_id)
                    ], limit=1)
                    
                    if not variant_value:
                        return request.make_json_response({'error': 'Variant value not found'}, status=404)
                    
                    if variant_value.create_uid.id != current_user_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only modify variant values you own'
                        }, status=403)
                
                elif entity_type == 'wifi':
                    shop_id = kwargs.get('shop_id')
                    wifi_id = kwargs.get('wifi_id')
                    
                    if not shop_id:
                        return request.make_json_response({'error': 'Shop ID is required'}, status=400)
                    
                    # For wifi creation, check shop ownership
                    if not wifi_id:
                        shop = request.env['res.partner'].sudo().search([
                            ('id', '=', shop_id),
                            ('type', '=', 'store')
                        ], limit=1)
                        
                        if not shop:
                            return request.make_json_response({'error': 'Shop not found'}, status=404)
                        
                        if shop.create_uid.id != current_user_id:
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only create wifi for shops you own'
                            }, status=403)
                    else:
                        # For wifi update/delete, check wifi ownership
                        wifi = request.env['shop.wifi'].sudo().search([
                            ('id', '=', wifi_id),
                            ('shop_id', '=', shop_id)
                        ], limit=1)
                        
                        if not wifi:
                            return request.make_json_response({'error': 'WiFi not found'}, status=404)
                        
                        if wifi.create_uid.id != current_user_id:
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only modify wifi you own'
                            }, status=403)
                
                elif entity_type == 'open_hour':
                    shop_id = kwargs.get('shop_id')
                    hour_id = kwargs.get('hour_id')
                    
                    if not shop_id:
                        return request.make_json_response({'error': 'Shop ID is required'}, status=400)
                    
                    # For open hour creation, check shop ownership
                    if not hour_id:
                        shop = request.env['res.partner'].sudo().search([
                            ('id', '=', shop_id),
                            ('type', '=', 'store')
                        ], limit=1)
                        
                        if not shop:
                            return request.make_json_response({'error': 'Shop not found'}, status=404)
                        
                        if shop.create_uid.id != current_user_id:
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only create open hours for shops you own'
                            }, status=403)
                    else:
                        # For open hour update/delete, check open hour ownership
                        open_hour = request.env['shop.open.hour'].sudo().search([
                            ('id', '=', hour_id),
                            ('shop_id', '=', shop_id)
                        ], limit=1)
                        
                        if not open_hour:
                            return request.make_json_response({'error': 'Open hour not found'}, status=404)
                        
                        if open_hour.create_uid.id != current_user_id:
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only modify open hours you own'
                            }, status=403)
                
                elif entity_type == 'banner':
                    shop_id = kwargs.get('shop_id')
                    
                    if not shop_id:
                        return request.make_json_response({'error': 'Shop ID is required'}, status=400)
                    
                    shop = request.env['res.partner'].sudo().search([
                        ('id', '=', shop_id),
                        ('type', '=', 'store')
                    ], limit=1)
                    
                    if not shop:
                        return request.make_json_response({'error': 'Shop not found'}, status=404)
                    
                    if shop.create_uid.id != current_user_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only update banners for shops you own'
                        }, status=403)
                
                return func(*args, **kwargs)
                
            except Exception as e:
                return request.make_json_response({'error': f'Authorization check failed: {str(e)}'}, status=500)
        
        return wrapper
    return decorator


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

        # Get secret key from Odoo configuration
        secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret', 'your-secret-key-here')
        token = jwt.encode(payload, secret_key, algorithm='HS256')

        return token

    def _validate_token(self, token, token_type='access'):
        """
        Validate an access or refresh token.

        Args:
            token (str): The token to validate
            token_type (str): Type of token ('access' or 'refresh')

        Returns:
            int or False: User ID if valid, False otherwise
        """
        import hashlib
        
        # Hash the token for database search
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # Search for the token in the database
        token_model = request.env['res.user.token'].sudo()
        domain = [
            ('access_token' if token_type == 'access' else 'refresh_token', '=', hashed_token),
            ('active', '=', True)
        ]
        
        token_record = token_model.search(domain, limit=1)
        
        if token_record:
            # Check if token is not expired
            expiry_field = 'expires_at' if token_type == 'access' else 'refresh_expires_at'
            if fields.Datetime.now() < token_record[expiry_field]:
                return token_record.user_id.id
        
        return False

    def _get_user_from_token(self, token, token_type='access'):
        """
        Get user object from a valid token.

        Args:
            token (str): The token to validate
            token_type (str): Type of token ('access' or 'refresh')

        Returns:
            res.users or None: User object if valid, None otherwise
        """
        user_id = self._validate_token(token, token_type)
        if user_id:
            return request.env['res.users'].sudo().browse(user_id)
        return None

    def _revoke_all_user_tokens(self, user_id):
        """
        Revoke all active tokens for a specific user.

        Args:
            user_id (int): The ID of the user whose tokens should be revoked

        Returns:
            bool: True if tokens were revoked, False otherwise
        """
        try:
            token_model = request.env['res.user.token'].sudo()
            active_tokens = token_model.search([
                ('user_id', '=', user_id),
                ('active', '=', True)
            ])
            
            if active_tokens:
                active_tokens.write({
                    'active': False,
                    'deactivated_at': fields.Datetime.now()
                })
                return True
            return False
        except Exception:
            return False

    def _get_token_info(self, token, token_type='access'):
        """
        Get detailed information about a token.

        Args:
            token (str): The token to get information for
            token_type (str): Type of token ('access' or 'refresh')

        Returns:
            dict or None: Token information if valid, None otherwise
        """
        import hashlib
        
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        token_model = request.env['res.user.token'].sudo()
        
        domain = [
            ('access_token' if token_type == 'access' else 'refresh_token', '=', hashed_token),
            ('active', '=', True)
        ]
        
        token_record = token_model.search(domain, limit=1)
        
        if token_record:
            expiry_field = 'expires_at' if token_type == 'access' else 'refresh_expires_at'
            remaining = token_record[expiry_field] - fields.Datetime.now()
            expires_in = max(0, int(remaining.total_seconds()))
            
            return {
                'user_id': token_record.user_id.id,
                'username': token_record.user_id.login,
                'expires_at': token_record[expiry_field].isoformat() if token_record[expiry_field] else None,
                'expires_in': expires_in,
                'is_expired': expires_in <= 0
            }
        
        return None

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
    @http.route(f"{BASE_URL}/my/order", auth="angkit", type="http", methods=["GET"], cors="*", csrf=False)
    def my_order(self, **kwargs):
        """
        Retrieve paginated list of orders for the authenticated user with search and ordering capabilities.

        Route: GET /angkort/api/v1/my/order

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for name, state, or date_order.
            order_by (str, optional): Field to order by (id, name, date_order). Default: date_order.
            order_direction (str, optional): Order direction (asc, desc). Default: desc.

        Returns:
            200: Paginated list of user orders.
            400: Invalid parameters.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "SO001",
                        "date_order": "01-01-2024",
                        "total": 100.0,
                        "state": "Quotation"
                    }
                ],
                "meta": {
                    "pagination": {
                        "total": 10,
                        "page": 1,
                        "limit": 20,
                        "pages": 1
                    },
                    "search": "SO001",
                    "order_by": "date_order",
                    "order_direction": "desc"
                }
            }
        """
        try:
            # Parse and validate pagination parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            offset = (page - 1) * limit
            
            # Parse search parameter
            search_term = request.httprequest.args.get('search', '').strip()
            
            # Parse and validate ordering parameters
            order_by = request.httprequest.args.get('order_by', 'date_order')
            order_direction = request.httprequest.args.get('order_direction', 'desc').lower()
            
            # Validate order_by field
            valid_order_fields = {'id', 'name', 'date_order'}
            if order_by not in valid_order_fields:
                return request.make_json_response(
                    {'error': f'Invalid order_by field. Must be one of: {", ".join(valid_order_fields)}'}, 
                    status=400
                )
            
            # Validate order direction
            if order_direction not in {'asc', 'desc'}:
                return request.make_json_response(
                    {'error': 'Invalid order_direction. Must be "asc" or "desc"'}, 
                    status=400
                )
            
            # Build domain with search functionality
            domain = [('partner_id', '=', request.env.user.partner_id.id)]
            
            if search_term:
                # Create search domain for name, state, and date_order
                search_domain = [
                    '|', '|',
                    ('name', 'ilike', search_term),
                    ('state', 'ilike', search_term),
                    ('date_order', 'ilike', search_term)
                ]
                domain = ['&'] + domain + search_domain
            
            # Build order clause
            order_clause = f"{order_by} {order_direction}"
            
            # Use sudo() for better performance and get total count
            sale_order_model = request.env['sale.order'].sudo()
            total = sale_order_model.search_count(domain)
            
            # Calculate pagination
            pages = (total + limit - 1) // limit
            page = min(max(1, page), pages) if pages > 0 else 1
            
            # Fetch orders with optimized query
            sales = sale_order_model.search(
                domain,
                offset=offset,
                limit=limit,
                order=order_clause
            )
            
            # Optimize data retrieval by selecting only needed fields and process in one pass
            orders_data = []
            for sale in sales:
                orders_data.append({
                    'id': sale.id,
                    'name': sale.name,
                    'date_order': sale.date_order.strftime('%d-%m-%Y') if sale.date_order else '',
                    'total': sale.amount_total,
                    'state': ORDER_STATE.get(sale.state, sale.state)
                })
            
            # Build response with optimized structure
            response = {
                'data': orders_data,
                'meta': {
                    'pagination': {
                        'total': total,
                        'page': page,
                        'limit': limit,
                        'pages': pages
                    },
                    'search': search_term if search_term else None,
                    'order_by': order_by,
                    'order_direction': order_direction
                }
            }
            
            return request.make_json_response(response, status=200)
            
        except ValueError as e:
            return request.make_json_response(
                {'error': f'Invalid parameter value: {str(e)}'}, 
                status=400
            )
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f'{BASE_URL}/my/order/<int:order_id>', auth="angkit", type="http", methods=["GET"], cors="*", csrf=False)
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

    @http.route(f"{BASE_URL}/cart/checkout", auth="angkit", type="json", methods=["POST"], cors="*", csrf=False)
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
    @http.route(f"{BASE_URL}/shop", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def shop_list(self, **kw):
        """
        Retrieve a paginated list of all shops with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/shop

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for shop name, phone, or address.
            sort (str, optional): Sort field (id, name, create_date). Default: id.
            order (str, optional): Sort order (asc, desc). Default: asc.
            filter_industry (str, optional): Filter by industry name.
            filter_has_wifi (bool, optional): Filter shops with/without WiFi.

        Returns:
            200: Paginated list of shops with pagination metadata.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Shop A",
                        "phoneNumber": ["123456789"],
                        "address": ["123 Main St"],
                        "wifi": ["ShopWiFi"],
                        "banks": [...],
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "coffee",
                        "sort": "name",
                        "order": "asc",
                        "filter": {
                            "industry": "Food & Beverage",
                            "has_wifi": true
                        }
                    }
                }
            }
        """
        try:
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'id')
            order = request.httprequest.args.get('order', 'asc').lower()
            filter_industry = request.httprequest.args.get('filter_industry', '').strip()
            filter_has_wifi = request.httprequest.args.get('filter_has_wifi', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'id'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = [('type', '=', 'store')]
            
            # Add search functionality
            if search:
                search_domain = [
                    '|', '|',
                    ('name', 'ilike', search),
                    ('phone', 'ilike', search),
                    ('customer_address', 'ilike', search)
                ]
                domain = ['&'] + domain + search_domain
            
            # Add filters
            if filter_industry:
                domain.append(('industry_id.name', 'ilike', filter_industry))
            
            if filter_has_wifi:
                if filter_has_wifi.lower() == 'true':
                    domain.append(('shop_wifi_ids', '!=', False))
                elif filter_has_wifi.lower() == 'false':
                    domain.append(('shop_wifi_ids', '=', False))
            
            # Calculate pagination
            offset = (page - 1) * limit
            stores_sudo = request.env['res.partner'].sudo()
            total = stores_sudo.search_count(domain)
            page_count = (total + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch shops
            stores = stores_sudo.search(
                domain,
                offset=offset,
                limit=limit,
                order=order_clause
            )
            
            shops_data = [{
                'id': shop.id,
                'name': shop.name or '',
                'phoneNumber': self._string_to_string_list(shop.phone) or [],
                "address": [shop.customer_address] if shop.customer_address else [],
                'wifi': self._string_to_string_list(shop.wifi_name) or [],
                'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids],
                'shop_wifi_ids': [{
                    'id': wifi.id,
                    'name': wifi.name,
                    'password': wifi.password,
                    'wifi_qr_code': wifi.wifi_qr_code.decode('utf-8') if wifi.wifi_qr_code else ''
                } for wifi in shop.shop_wifi_ids],
                'shop_open_hour_ids': [{
                    'id': hour.id,
                    'day': hour.day,
                    'day_name': dict(hour._fields['day'].selection).get(hour.day, ''),
                    'open': hour.open,
                    'close': hour.close
                } for hour in shop.shop_open_hour_ids],
                'createdAt': shop.create_date.isoformat() if shop.create_date else None,
                'updatedAt': shop.write_date.isoformat() if shop.write_date else None,
                'publishedAt': shop.create_date.isoformat() if shop.create_date else None
            } for shop in stores]
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_industry:
                keyword_meta["filter"]["industry"] = filter_industry
            if filter_has_wifi:
                keyword_meta["filter"]["has_wifi"] = filter_has_wifi.lower() == 'true'
            
            response = {
                'data': shops_data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total
                    },
                    'keyword': keyword_meta
                }
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
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
                "data": {
                    "id": 1,
                    "name": "Shop A",
                    "phoneNumber": ["123456789"],
                    "address": ["123 Main St"],
                    "wifi": ["ShopWiFi"],
                    "banks": [...],
                    "createdAt": "2024-03-06T13:42:05.098Z",
                    "updatedAt": "2024-03-06T13:42:05.098Z",
                    "publishedAt": "2024-03-06T13:42:05.103Z"
                }
            }
        """
        try:
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            response = {
                'data': {
                    'id': shop.id,
                    'name': shop.name or '',
                    'phoneNumber': self._string_to_string_list(shop.phone) or [],
                    "address": [shop.customer_address] if shop.customer_address else [],
                    'wifi': self._string_to_string_list(shop.wifi_name) or [],
                    'shop_wifi_ids': [{
                        'id': wifi.id,
                        'name': wifi.name,
                        'password': wifi.password,
                        'wifi_qr_code': wifi.wifi_qr_code.decode('utf-8') if wifi.wifi_qr_code else ''
                    } for wifi in shop.shop_wifi_ids],
                    'shop_open_hour_ids': [{
                        'id': hour.id,
                        'day': hour.day,
                        'day_name': dict(hour._fields['day'].selection).get(hour.day, ''),
                        'open': hour.open,
                        'close': hour.close
                    } for hour in shop.shop_open_hour_ids],
                    'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids],
                    'createdAt': shop.create_date.isoformat() if shop.create_date else None,
                    'updatedAt': shop.write_date.isoformat() if shop.write_date else None,
                    'publishedAt': shop.create_date.isoformat() if shop.create_date else None
                }
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
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
            
            # Validate required fields
            required_fields = ['name', 'phone', 'customer_address']
            missing_fields = [field for field in required_fields if not create_data.get(field)]
            
            if missing_fields:
                errors = []
                for field in missing_fields:
                    if field == 'name':
                        errors.append({"name": "name", "message": "Shop name is required"})
                    elif field == 'phone':
                        errors.append({"name": "phone", "message": "Phone number is required"})
                    elif field == 'customer_address':
                        errors.append({"name": "customer_address", "message": "Shop address is required"})
                
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create shop",
                    "statusCode": "400",
                    "errors": errors
                }), status=400, content_type='application/json')
            
            shop = request.env['res.partner'].sudo().with_context(create_company=True).create([create_data])
            if shop:
                request.env.user.partner_id.update({'parent_id': shop.id})
            resp = {'id': shop.id, 'name': shop.name}
            return Response(json.dumps(resp), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='shop')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update shop",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in PARTNER_FIELDS}
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update shop",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            shop.write(update_fields)
            return Response(json.dumps({'message': f'Shop with ID {shop_id} updated successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", csrf=False, methods=["PATCH"], cors="*")
    @verify_ownership(entity_type='shop')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch shop",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in PARTNER_FIELDS}
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch shop",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            shop.write(update_fields)
            return Response(json.dumps({'message': f'Shop with ID {shop_id} patched successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to patch shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='shop')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete shop",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }), status=404, content_type='application/json')
            shop.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/wifi", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='wifi')
    def shop_wifi_create(self, shop_id, **kw):
        """
        Create a new WiFi entry for a shop.

        Route: POST /angkort/api/v1/shop/<shop_id>/wifi

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            name (str): WiFi name (required).
            password (str): WiFi password (required).
            wifi_qr_code (file, optional): WiFi QR code image.

        Returns:
            201: Created WiFi details.
            400: If required fields are missing.
            404: If the shop is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            wifi_qr_code_file = request.httprequest.files.get('wifi_qr_code')
            
            # Validate required fields
            if 'name' not in data or 'password' not in data:
                errors = []
                if 'name' not in data:
                    errors.append({"name": "name", "message": "WiFi name is required"})
                if 'password' not in data:
                    errors.append({"name": "password", "message": "WiFi password is required"})
                
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create WiFi",
                    "statusCode": "400",
                    "errors": errors
                }), status=400, content_type='application/json')
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Prepare WiFi data
            wifi_data = {
                'name': data['name'],
                'password': data['password'],
                'shop_id': shop_id
            }
            
            # Handle QR code image if provided
            if wifi_qr_code_file:
                image_data = wifi_qr_code_file.read()
                wifi_data['wifi_qr_code'] = base64.b64encode(image_data)
            
            # Create WiFi entry
            wifi = request.env['shop.wifi'].sudo().create(wifi_data)
            
            response_data = {
                'id': wifi.id,
                'name': wifi.name,
                'password': wifi.password,
                'wifi_qr_code': wifi.wifi_qr_code.decode('utf-8') if wifi.wifi_qr_code else ''
            }
            
            return Response(json.dumps(response_data), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create WiFi",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/wifi/<int:wifi_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='wifi')
    def shop_wifi_update(self, shop_id, wifi_id, **kw):
        """
        Update a WiFi entry for a shop.

        Route: PUT /angkort/api/v1/shop/<shop_id>/wifi/<wifi_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            wifi_id (int): The ID of the WiFi entry.
            name (str, optional): New WiFi name.
            password (str, optional): New WiFi password.
            wifi_qr_code (file, optional): New WiFi QR code image.

        Returns:
            200: Updated WiFi details.
            400: If no valid fields to update.
            404: If the shop or WiFi is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            wifi_qr_code_file = request.httprequest.files.get('wifi_qr_code')
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Verify WiFi exists and belongs to shop
            wifi = request.env['shop.wifi'].sudo().search([('id', '=', wifi_id), ('shop_id', '=', shop_id)], limit=1)
            if not wifi:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "wifi_id", "message": "WiFi not found"}]
                }), status=404, content_type='application/json')
            
            # Prepare update data
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'password' in data:
                update_data['password'] = data['password']
            
            # Handle QR code image if provided
            if wifi_qr_code_file:
                image_data = wifi_qr_code_file.read()
                update_data['wifi_qr_code'] = base64.b64encode(image_data)
            
            if not update_data:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update WiFi",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            
            # Update WiFi entry
            wifi.write(update_data)
            
            response_data = {
                'id': wifi.id,
                'name': wifi.name,
                'password': wifi.password,
                'wifi_qr_code': wifi.wifi_qr_code.decode('utf-8') if wifi.wifi_qr_code else ''
            }
            
            return Response(json.dumps(response_data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update WiFi",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/wifi/<int:wifi_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='wifi')
    def shop_wifi_delete(self, shop_id, wifi_id, **kw):
        """
        Delete a WiFi entry from a shop.

        Route: DELETE /angkort/api/v1/shop/<shop_id>/wifi/<wifi_id>

        Parameters:
            shop_id (int): The ID of the shop.
            wifi_id (int): The ID of the WiFi entry.

        Returns:
            204: On successful deletion.
            404: If the shop or WiFi is not found.
            500: On server error.
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Verify WiFi exists and belongs to shop
            wifi = request.env['shop.wifi'].sudo().search([('id', '=', wifi_id), ('shop_id', '=', shop_id)], limit=1)
            if not wifi:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "wifi_id", "message": "WiFi not found"}]
                }), status=404, content_type='application/json')
            
            # Delete WiFi entry
            wifi.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete WiFi",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/banner", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='banner')
    def shop_banner_update(self, shop_id, **kw):
        """
        Update shop banner image.

        Route: POST /angkort/api/v1/shop/<shop_id>/banner

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            shop_banner (file): Shop banner image (required).

        Returns:
            200: Success message with banner URL.
            400: If no banner image provided.
            404: If the shop is not found.
            500: On server error.
        """
        try:
            banner_file = request.httprequest.files.get('shop_banner')
            
            if not banner_file:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update banner",
                    "statusCode": "400",
                    "errors": [{"name": "shop_banner", "message": "Banner image is required"}]
                }), status=400, content_type='application/json')
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update banner",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Read and encode banner image
            image_data = banner_file.read()
            encoded_image = base64.b64encode(image_data)
            
            # Update shop banner
            shop.write({'shop_banner': encoded_image})
            
            response_data = {
                'message': 'Banner updated successfully',
                'banner_url': f'/web/image/res.partner/{shop_id}/shop_banner'
            }
            
            return Response(json.dumps(response_data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update banner",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/open-hours", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='open_hour')
    def shop_open_hours_create(self, shop_id, **kw):
        """
        Create a new open hour entry for a shop.

        Route: POST /angkort/api/v1/shop/<shop_id>/open-hours

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            day (str): Day of week (0-6, where 0=Monday) (required).
            open (str): Opening time (required).
            close (str): Closing time (required).

        Returns:
            201: Created open hour details.
            400: If required fields are missing or invalid.
            404: If the shop is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            
            # Validate required fields
            if 'day' not in data or 'open' not in data or 'close' not in data:
                errors = []
                if 'day' not in data:
                    errors.append({"name": "day", "message": "Day is required"})
                if 'open' not in data:
                    errors.append({"name": "open", "message": "Opening time is required"})
                if 'close' not in data:
                    errors.append({"name": "close", "message": "Closing time is required"})
                
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "400",
                    "errors": errors
                }), status=400, content_type='application/json')
            
            # Validate day value
            valid_days = ['0', '1', '2', '3', '4', '5', '6']
            if data['day'] not in valid_days:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "400",
                    "errors": [{"name": "day", "message": "Day must be between 0-6 (0=Monday, 6=Sunday)"}]
                }), status=400, content_type='application/json')
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Check if open hour for this day already exists
            existing_hour = request.env['shop.open.hour'].sudo().search([
                ('shop_id', '=', shop_id),
                ('day', '=', data['day'])
            ], limit=1)
            
            if existing_hour:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "400",
                    "errors": [{"name": "day", "message": "Open hour for this day already exists"}]
                }), status=400, content_type='application/json')
            
            # Create open hour entry
            open_hour_data = {
                'day': data['day'],
                'open': data['open'],
                'close': data['close'],
                'shop_id': shop_id
            }
            
            open_hour = request.env['shop.open.hour'].sudo().create(open_hour_data)
            
            response_data = {
                'id': open_hour.id,
                'day': open_hour.day,
                'day_name': dict(open_hour._fields['day'].selection).get(open_hour.day, ''),
                'open': open_hour.open,
                'close': open_hour.close
            }
            
            return Response(json.dumps(response_data), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create open hour",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/open-hours/<int:hour_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='open_hour')
    def shop_open_hours_update(self, shop_id, hour_id, **kw):
        """
        Update an open hour entry for a shop.

        Route: PUT /angkort/api/v1/shop/<shop_id>/open-hours/<hour_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            hour_id (int): The ID of the open hour entry.
            day (str, optional): Day of week (0-6, where 0=Monday).
            open (str, optional): Opening time.
            close (str, optional): Closing time.

        Returns:
            200: Updated open hour details.
            400: If no valid fields to update or invalid data.
            404: If the shop or open hour is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update open hour",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Verify open hour exists and belongs to shop
            open_hour = request.env['shop.open.hour'].sudo().search([('id', '=', hour_id), ('shop_id', '=', shop_id)], limit=1)
            if not open_hour:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update open hour",
                    "statusCode": "404",
                    "errors": [{"name": "hour_id", "message": "Open hour not found"}]
                }), status=404, content_type='application/json')
            
            # Validate day value if provided
            if 'day' in data:
                valid_days = ['0', '1', '2', '3', '4', '5', '6']
                if data['day'] not in valid_days:
                    return Response(json.dumps({
                        "status": "error",
                        "message": "Failed to update open hour",
                        "statusCode": "400",
                        "errors": [{"name": "day", "message": "Day must be between 0-6 (0=Monday, 6=Sunday)"}]
                    }), status=400, content_type='application/json')
                
                # Check if day is being changed and if new day already exists
                if data['day'] != open_hour.day:
                    existing_hour = request.env['shop.open.hour'].sudo().search([
                        ('shop_id', '=', shop_id),
                        ('day', '=', data['day']),
                        ('id', '!=', hour_id)
                    ], limit=1)
                    
                    if existing_hour:
                        return Response(json.dumps({
                            "status": "error",
                            "message": "Failed to update open hour",
                            "statusCode": "400",
                            "errors": [{"name": "day", "message": "Open hour for this day already exists"}]
                        }), status=400, content_type='application/json')
            
            # Prepare update data
            update_data = {}
            if 'day' in data:
                update_data['day'] = data['day']
            if 'open' in data:
                update_data['open'] = data['open']
            if 'close' in data:
                update_data['close'] = data['close']
            
            if not update_data:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update open hour",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            
            # Update open hour entry
            open_hour.write(update_data)
            
            response_data = {
                'id': open_hour.id,
                'day': open_hour.day,
                'day_name': dict(open_hour._fields['day'].selection).get(open_hour.day, ''),
                'open': open_hour.open,
                'close': open_hour.close
            }
            
            return Response(json.dumps(response_data), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update open hour",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/open-hours/<int:hour_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='open_hour')
    def shop_open_hours_delete(self, shop_id, hour_id, **kw):
        """
        Delete an open hour entry from a shop.

        Route: DELETE /angkort/api/v1/shop/<shop_id>/open-hours/<hour_id>

        Parameters:
            shop_id (int): The ID of the shop.
            hour_id (int): The ID of the open hour entry.

        Returns:
            204: On successful deletion.
            404: If the shop or open hour is not found.
            500: On server error.
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete open hour",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            # Verify open hour exists and belongs to shop
            open_hour = request.env['shop.open.hour'].sudo().search([('id', '=', hour_id), ('shop_id', '=', shop_id)], limit=1)
            if not open_hour:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete open hour",
                    "statusCode": "404",
                    "errors": [{"name": "hour_id", "message": "Open hour not found"}]
                }), status=404, content_type='application/json')
            
            # Delete open hour entry
            open_hour.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete open hour",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/create", auth="angkit", type="http", csrf=False, cors="*", methods=["POST"])
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
                errors = []
                for field in missing_fields:
                    if field == 'name':
                        errors.append({"name": "name", "message": "Shop name is required"})
                    elif field == 'phone':
                        errors.append({"name": "phone", "message": "Phone number is required"})
                    elif field == 'customer_address':
                        errors.append({"name": "customer_address", "message": "Shop address is required"})
                
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create shop",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)
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
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def product_list(self, shop_id, **kw):
        """
        Retrieve all products for a given shop with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/shop/<shop_id>/product

        Parameters:
            shop_id (int): The ID of the shop.

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for product name, code, or description.
            sort (str, optional): Sort field (id, name, list_price, create_date). Default: id.
            order (str, optional): Sort order (asc, desc). Default: asc.
            filter_category (int, optional): Filter by category ID.
            filter_price_min (float, optional): Minimum price filter.
            filter_price_max (float, optional): Maximum price filter.
            filter_has_variants (bool, optional): Filter products with/without variants.

        Returns:
            200: List of products with their details.
            404: If the shop is not found.
            500: On server error.

        Example Response:
            {
                "data": [
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
                        },
                        "options": [...],
                        "choices": [...],
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "coffee",
                        "sort": "list_price",
                        "order": "desc",
                        "filter": {
                            "category": 1,
                            "price_min": 10.0,
                            "price_max": 100.0,
                            "has_variants": true
                        }
                    }
                }
            }
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'id')
            order = request.httprequest.args.get('order', 'asc').lower()
            filter_category = request.httprequest.args.get('filter_category', '').strip()
            filter_price_min = request.httprequest.args.get('filter_price_min', '').strip()
            filter_price_max = request.httprequest.args.get('filter_price_max', '').strip()
            filter_has_variants = request.httprequest.args.get('filter_has_variants', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'list_price', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'id'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = [('shop_id', '=', shop_id)]
            
            # Add search functionality
            if search:
                search_domain = [
                    '|', '|',
                    ('name', 'ilike', search),
                    ('default_code', 'ilike', search),
                    ('description', 'ilike', search)
                ]
                domain = ['&'] + domain + search_domain
            
            # Add filters
            if filter_category:
                try:
                    category_id = int(filter_category)
                    domain.append(('categ_id', '=', category_id))
                except ValueError:
                    pass
            
            if filter_price_min:
                try:
                    price_min = float(filter_price_min)
                    domain.append(('list_price', '>=', price_min))
                except ValueError:
                    pass
            
            if filter_price_max:
                try:
                    price_max = float(filter_price_max)
                    domain.append(('list_price', '<=', price_max))
                except ValueError:
                    pass
            
            if filter_has_variants:
                if filter_has_variants.lower() == 'true':
                    domain.append(('attribute_line_ids', '!=', False))
                elif filter_has_variants.lower() == 'false':
                    domain.append(('attribute_line_ids', '=', False))
            
            # Calculate pagination
            offset = (page - 1) * limit
            total = request.env['product.product'].sudo().search_count(domain)
            page_count = (total + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch products
            products = request.env['product.product'].sudo().search(
                domain,
                offset=offset,
                limit=limit,
                order=order_clause
            )
            
            data = []
            for product in products:
                tmp_data = self._product_to_dict(product)
                tmp_data['options'] = [self._get_product_options(option) for option in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'radio')]
                tmp_data['choices'] = [self._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'multi')]
                tmp_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
                tmp_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
                tmp_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
                data.append(tmp_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_category:
                keyword_meta["filter"]["category"] = int(filter_category)
            if filter_price_min:
                keyword_meta["filter"]["price_min"] = float(filter_price_min)
            if filter_price_max:
                keyword_meta["filter"]["price_max"] = float(filter_price_max)
            if filter_has_variants:
                keyword_meta["filter"]["has_variants"] = filter_has_variants.lower() == 'true'
            
            response = {
                'data': data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total
                    },
                    'keyword': keyword_meta
                }
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
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
                "data": {
                    "id": 1,
                    "name": "Product A",
                    "code": "PROD001",
                    "description": "Product description",
                    "sale_price": 99.99,
                    "image": "base64_image_data",
                    "category": {
                        "id": 1,
                        "name": "Electronics"
                    },
                    "options": [...],
                    "choices": [...],
                    "createdAt": "2024-03-06T13:42:05.098Z",
                    "updatedAt": "2024-03-06T13:42:05.098Z",
                    "publishedAt": "2024-03-06T13:42:05.103Z"
                }
            }
        """
        try:
            product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)], limit=1)
            if not product:
                return Response(json.dumps({'error': 'Product not found'}), status=404, content_type='application/json')
            product_data = self._get_product_details(product)
            product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
            product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
            product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
            response = {
                'data': product_data
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='shop')
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
                errors = []
                for field in missing_fields:
                    if field == 'name':
                        errors.append({"name": "name", "message": "Product name is required"})
                    elif field == 'price':
                        errors.append({"name": "price", "message": "Product price is required"})
                    elif field == 'category_id':
                        errors.append({"name": "category_id", "message": "Category ID is required"})
                
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create product",
                    "statusCode": "400",
                    "errors": errors
                }), status=400, content_type='application/json')
            
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create product",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }), status=404, content_type='application/json')
            
            category = request.env['product.category'].sudo().search([('id', '=', data.get('category_id'))], limit=1)
            if not category:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create product",
                    "statusCode": "404",
                    "errors": [{"name": "category_id", "message": f"Category with ID {data.get('category_id')} not found"}]
                }), status=404, content_type='application/json')
            
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
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create product",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="angkit", methods=["PUT"], cors="*", csrf=False)
    @verify_ownership(entity_type='product')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update product",
                    "statusCode": "404",
                    "errors": [{"name": "product_id", "message": f"Product with ID {product_id} not found"}]
                }), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'list_price', 'categ_id', 'description', 'barcode', 'qty_available']}
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                update_fields['image_1920'] = encoded_image
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update product",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            product.write(update_fields)
            return Response(json.dumps({'message': f'Product with ID {product_id} updated successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update product",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="angkit", methods=["PATCH"], cors="*", csrf=False)
    @verify_ownership(entity_type='product')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch product",
                    "statusCode": "404",
                    "errors": [{"name": "product_id", "message": f"Product with ID {product_id} not found"}]
                }), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name', 'list_price', 'categ_id', 'description', 'barcode', 'qty_available']}
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                update_fields['image_1920'] = encoded_image
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch product",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            product.write(update_fields)
            return Response(json.dumps({'message': f'Product with ID {product_id} patched successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to patch product",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>", type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='product')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete product",
                    "statusCode": "404",
                    "errors": [{"name": "product_id", "message": f"Product with ID {product_id} not found"}]
                }), status=404, content_type='application/json')
            product.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete product",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/calculate-price", auth="angkit", type="http", csrf=False, cors="*")
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

    @http.route(f"{BASE_URL}/industries", methods=['GET'], auth="public", type="http", cors="*")
    def industries(self, **kw):
        """
        Retrieve a paginated list of all available industries with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/industries

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for industry name or full name.
            sort (str, optional): Sort field (id, name, full_name, create_date). Default: name.
            order (str, optional): Sort order (asc, desc). Default: asc.

        Returns:
            200: Paginated list of industries with pagination metadata.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "full_name": "Information Technology",
                        "name": "IT",
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "technology",
                        "sort": "name",
                        "order": "asc"
                    }
                }
            }
        """
        try:
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'name')
            order = request.httprequest.args.get('order', 'asc').lower()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'full_name', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'name'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = []
            
            # Add search functionality
            if search:
                search_domain = [
                    '|',
                    ('name', 'ilike', search),
                    ('full_name', 'ilike', search)
                ]
                domain = search_domain
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_count = request.env['res.partner.industry'].sudo().search_count(domain)
            page_count = (total_count + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch industries
            industries = request.env['res.partner.industry'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order=order_clause
            )
            
            industries_data = []
            for industry in industries:
                industry_data = {
                    'id': industry.id,
                    'full_name': getattr(industry, 'full_name', industry.name),
                    'name': industry.name,
                    'createdAt': industry.create_date.isoformat() if industry.create_date else None,
                    'updatedAt': industry.write_date.isoformat() if industry.write_date else None,
                    'publishedAt': industry.create_date.isoformat() if industry.create_date else None
                }
                industries_data.append(industry_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order
            }
            
            response = {
                'data': industries_data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total_count
                    },
                    'keyword': keyword_meta
                }
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({
                'error': 'Error retrieving industries',
                'message': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/login", auth="public", type="http", csrf=False, cors="*", methods=["POST"])
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
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'token_type': 'Bearer',
                        'expires_in': 1800,  # 30 minutes in seconds
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

    @http.route(f"{BASE_URL}/logout", auth="angkit", type="http", csrf=False, cors="*", methods=["POST"])
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

    @http.route(f"{BASE_URL}/refresh", auth="public", type="http", csrf=False, cors="*", methods=["POST"])
    def refresh_token(self):
        """
        Generate a new access token using a valid refresh token.

        Route: POST /angkort/api/v1/refresh

        Parameters (JSON body):
            refresh_token (str): The refresh token to generate new access token (required).

        Returns:
            200: New access token generated successfully.
            400: If refresh token is missing or invalid.
            401: If refresh token is expired or invalid.
            500: On server error.

        Example Request:
            {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }

        Example Response:
            {
                "status": true,
                "message": "Token refreshed successfully",
                "data": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer",
                    "expires_in": 1800,
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

            refresh_token = data.get('refresh_token')
            if not refresh_token:
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing required field',
                    'error': 'refresh_token is required'
                }, status=400)

            # Validate the refresh token and get user
            user = self._get_user_from_token(refresh_token, 'refresh')
            if not user:
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid refresh token',
                    'error': 'Refresh token is expired or invalid'
                }, status=401)

            # Generate new access token
            new_access_token = self._generate_token(user.id, 'access', minutes=30)

            # Store the new token in the database
            token_model = request.env['res.user.token'].sudo()
            token_model.create_token(
                user_id=user.id,
                access_token=new_access_token,
                refresh_token=refresh_token,  # Keep the same refresh token
                access_expiry=fields.Datetime.now() + timedelta(minutes=30),
                refresh_expiry=fields.Datetime.now() + timedelta(days=7)  # Keep refresh expiry unchanged
            )

            return request.make_json_response({
                'status': True,
                'message': 'Token refreshed successfully',
                'data': {
                    'access_token': new_access_token,
                    'token_type': 'Bearer',
                    'expires_in': 1800,  # 30 minutes in seconds
                    'user_id': user.id,
                    'username': user.login
                }
            }, status=200)

        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error refreshing token',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/validate", auth="public", type="http", csrf=False, cors="*", methods=["POST"])
    def validate_token(self):
        """
        Validate an access token and return user information.

        Route: POST /angkort/api/v1/validate

        Parameters (JSON body):
            access_token (str): The access token to validate (required).

        Returns:
            200: Token is valid with user information.
            400: If access token is missing.
            401: If access token is expired or invalid.
            500: On server error.

        Example Request:
            {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }

        Example Response:
            {
                "status": true,
                "message": "Token is valid",
                "data": {
                    "user_id": 1,
                    "username": "admin",
                    "expires_in": 1200
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

            access_token = data.get('access_token')
            if not access_token:
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing required field',
                    'error': 'access_token is required'
                }, status=400)

            # Validate the access token and get user
            user = self._get_user_from_token(access_token, 'access')
            if not user:
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid access token',
                    'error': 'Access token is expired or invalid'
                }, status=401)

            # Get token expiry information
            import hashlib
            hashed_token = hashlib.sha256(access_token.encode()).hexdigest()
            token_record = request.env['res.user.token'].sudo().search([
                ('access_token', '=', hashed_token),
                ('active', '=', True)
            ], limit=1)

            # Calculate remaining time
            expires_in = 0
            if token_record and token_record.expires_at:
                from datetime import datetime
                remaining = token_record.expires_at - fields.Datetime.now()
                expires_in = max(0, int(remaining.total_seconds()))

            return request.make_json_response({
                'status': True,
                'message': 'Token is valid',
                'data': {
                    'user_id': user.id,
                    'username': user.login,
                    'expires_in': expires_in
                }
            }, status=200)

        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error validating token',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/revoke-all", auth="angkit", type="http", csrf=False, cors="*", methods=["POST"])
    def revoke_all_tokens(self):
        """
        Revoke all active tokens for the authenticated user.

        Route: POST /angkort/api/v1/revoke-all

        Headers:
            Authorization: Bearer <access_token> (required)

        Returns:
            200: All tokens revoked successfully.
            401: If authentication fails.
            500: On server error.

        Example Response:
            {
                "status": true,
                "message": "All tokens revoked successfully",
                "data": {
                    "revoked_count": 3
                }
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

            # Validate the token belongs to the current user
            token_user = self._get_user_from_token(access_token, 'access')
            if not token_user or token_user.id != user.id:
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid token',
                    'error': 'Token does not belong to current user'
                }, status=401)

            # Get count of active tokens before revocation
            token_model = request.env['res.user.token'].sudo()
            active_tokens_count = token_model.search_count([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ])

            # Revoke all tokens
            revoked = self._revoke_all_user_tokens(user.id)

            if revoked:
                return request.make_json_response({
                    'status': True,
                    'message': 'All tokens revoked successfully',
                    'data': {
                        'revoked_count': active_tokens_count
                    }
                }, status=200)
            else:
                return request.make_json_response({
                    'status': False,
                    'message': 'No tokens to revoke',
                    'error': 'No active tokens found for user'
                }, status=400)

        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error revoking tokens',
                'error': str(e)
            }, status=500)

    # --- CATEGORY ROUTES ---
    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def category_list(self, shop_id, **kw):
        """
        Retrieve all product categories for a given shop with search and sort capabilities.

        Route: GET /angkort/api/v1/shop/<shop_id>/product/category

        Parameters:
            shop_id (int): The ID of the shop.

        Query Parameters:
            search (str, optional): Search term for category name.
            sort (str, optional): Sort field (id, name, create_date). Default: id.
            order (str, optional): Sort order (asc, desc). Default: asc.

        Returns:
            200: List of categories as JSON array.
            404: If the shop is not found.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Electronics",
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "keyword": {
                        "search": "electronics",
                        "sort": "name",
                        "order": "asc"
                    }
                }
            }
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            
            # Parse query parameters
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'id')
            order = request.httprequest.args.get('order', 'asc').lower()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'id'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = [('shop_id', '=', shop_id)]
            
            # Add search functionality
            if search:
                domain.append(('name', 'ilike', search))
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch categories
            categories = request.env['product.category'].sudo().search(
                domain,
                order=order_clause
            )
            
            data = []
            for category in categories:
                category_data = self._category_to_dict(category)
                category_data['createdAt'] = category.create_date.isoformat() if category.create_date else None
                category_data['updatedAt'] = category.write_date.isoformat() if category.write_date else None
                category_data['publishedAt'] = category.create_date.isoformat() if category.create_date else None
                data.append(category_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order
            }
            
            response = {
                'data': data,
                'meta': {
                    'keyword': keyword_meta
                }
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create category",
                    "statusCode": "400",
                    "errors": [{"name": "name", "message": "Category name is required"}]
                }), status=400, content_type='application/json')
            category = request.env['product.category'].sudo().create({
                'name': data['name'],
                'shop_id': shop_id,
            })
            return Response(json.dumps(self._category_to_dict(category)), status=201, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create category",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["PUT"], cors="http://localhost:3000,https://odoo.angkot.org,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080,http://localhost:8069,http://127.0.0.1:8069", csrf=False)
    @verify_ownership(entity_type='category')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update category",
                    "statusCode": "404",
                    "errors": [{"name": "cate_id", "message": "Category not found"}]
                }), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name']}
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update category",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            category.write(update_fields)
            return Response(json.dumps(self._category_to_dict(category)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update category",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["PATCH"], cors="http://localhost:3000,https://odoo.angkot.org,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080,http://localhost:8069,http://127.0.0.1:8069", csrf=False)
    @verify_ownership(entity_type='category')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch category",
                    "statusCode": "404",
                    "errors": [{"name": "cate_id", "message": "Category not found"}]
                }), status=404, content_type='application/json')
            update_fields = {k: v for k, v in data.items() if k in ['name']}
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch category",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            category.write(update_fields)
            return Response(json.dumps(self._category_to_dict(category)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to patch category",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>", type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='category')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete category",
                    "statusCode": "404",
                    "errors": [{"name": "cate_id", "message": "Category not found"}]
                }), status=404, content_type='application/json')
            category.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete category",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    # --- GLOBAL ROUTES (System-wide functionality) ---
    @http.route(f"{BASE_URL}/product/category", methods=['GET'], auth="public", type="http", cors="*")
    def global_product_category(self, **kw):
        """
        Retrieve a paginated list of all product categories (global, not shop-specific) with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/product/category

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for category name.
            sort (str, optional): Sort field (id, name, create_date). Default: name.
            order (str, optional): Sort order (asc, desc). Default: asc.
            filter_parent (int, optional): Filter by parent category ID.
            filter_has_children (bool, optional): Filter categories with/without children.

        Returns:
            200: Paginated list of all product categories with hierarchical information.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 15,
                        "name": "Electronics",
                        "parent_id": null,
                        "parent_name": null,
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "electronics",
                        "sort": "name",
                        "order": "asc",
                        "filter": {
                            "parent": null,
                            "has_children": true
                        }
                    }
                }
            }
        """
        try:
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'name')
            order = request.httprequest.args.get('order', 'asc').lower()
            filter_parent = request.httprequest.args.get('filter_parent', '').strip()
            filter_has_children = request.httprequest.args.get('filter_has_children', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'name'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = []
            
            # Add search functionality
            if search:
                domain.append(('name', 'ilike', search))
            
            # Add filters
            if filter_parent:
                if filter_parent.lower() == 'null':
                    domain.append(('parent_id', '=', False))
                else:
                    try:
                        parent_id = int(filter_parent)
                        domain.append(('parent_id', '=', parent_id))
                    except ValueError:
                        pass
            
            if filter_has_children:
                if filter_has_children.lower() == 'true':
                    domain.append(('child_id', '!=', False))
                elif filter_has_children.lower() == 'false':
                    domain.append(('child_id', '=', False))
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_count = request.env['product.category'].sudo().search_count(domain)
            page_count = (total_count + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch categories
            categories = request.env['product.category'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order=order_clause
            )
            
            categories_data = []
            for category in categories:
                category_data = {
                    'id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id.id if category.parent_id else None,
                    'parent_name': category.parent_id.name if category.parent_id else None,
                    'createdAt': category.create_date.isoformat() if category.create_date else None,
                    'updatedAt': category.write_date.isoformat() if category.write_date else None,
                    'publishedAt': category.create_date.isoformat() if category.create_date else None
                }
                categories_data.append(category_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_parent:
                if filter_parent.lower() == 'null':
                    keyword_meta["filter"]["parent"] = None
                else:
                    keyword_meta["filter"]["parent"] = int(filter_parent)
            if filter_has_children:
                keyword_meta["filter"]["has_children"] = filter_has_children.lower() == 'true'
            
            response = {
                'data': categories_data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total_count
                    },
                    'keyword': keyword_meta
                }
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({
                'error': 'Error retrieving product categories',
                'message': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/image/add", auth="angkit", type="http", methods=["POST"], cors="*", csrf=False)
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

    @http.route(f"{BASE_URL}/product/<int:product_id>", methods=['GET'], auth="public", type="http", cors="*")
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
                "data": {
                    "id": 1,
                    "name": "Product A",
                    "code": "PROD001",
                    "description": "Product description",
                    "sale_price": 99.99,
                    "image": "base64_image_data",
                    "category": {
                        "id": 1,
                        "name": "Electronics"
                    },
                    "options": [...],
                    "choices": [...],
                    "createdAt": "2024-03-06T13:42:05.098Z",
                    "updatedAt": "2024-03-06T13:42:05.098Z",
                    "publishedAt": "2024-03-06T13:42:05.103Z"
                }
            }
        """
        try:
            product = request.env['product.product'].sudo().search([('id', '=', product_id)], limit=1)
            if not product:
                return request.make_json_response({
                    'error': 'Product not found',
                    'message': 'Product does not exist'
                }, status=404)

            product_data = self._product_to_dict(product)
            product_data['options'] = [self._get_product_options(option) for option in product.attribute_line_ids.filtered(
                lambda x: x.attribute_id.display_type == 'radio')]
            product_data['choices'] = [self._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(
                lambda x: x.attribute_id.display_type == 'multi')]
            product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
            product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
            product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None

            response = {
                'data': product_data
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({
                'error': 'Error retrieving product',
                'message': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/product/variant", methods=['GET'], auth="public", type="http", cors="*")
    def global_product_variant(self, **kw):
        """
        Retrieve a paginated list of all product attributes (global, not shop-specific) with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/product/variant

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for attribute name.
            sort (str, optional): Sort field (id, name, create_date). Default: name.
            order (str, optional): Sort order (asc, desc). Default: asc.
            filter_create_variant (str, optional): Filter by create_variant type (no_variant, always).
            filter_display_type (str, optional): Filter by display_type (multi, radio).

        Returns:
            200: Paginated list of product attributes.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Color",
                        "create_variant": "always",
                        "display_type": "radio",
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "color",
                        "sort": "name",
                        "order": "asc",
                        "filter": {
                            "create_variant": "always",
                            "display_type": "radio"
                        }
                    }
                }
            }
        """
        try:
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'name')
            order = request.httprequest.args.get('order', 'asc').lower()
            filter_create_variant = request.httprequest.args.get('filter_create_variant', '').strip()
            filter_display_type = request.httprequest.args.get('filter_display_type', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'name'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = []
            
            # Add search functionality
            if search:
                domain.append(('name', 'ilike', search))
            
            # Add filters
            if filter_create_variant:
                if filter_create_variant in ['no_variant', 'always']:
                    domain.append(('create_variant', '=', filter_create_variant))
            
            if filter_display_type:
                if filter_display_type in ['multi', 'radio']:
                    domain.append(('display_type', '=', filter_display_type))
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_count = request.env['product.attribute'].sudo().search_count(domain)
            page_count = (total_count + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch attributes
            attributes = request.env['product.attribute'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order=order_clause
            )
            
            attributes_data = []
            for attribute in attributes:
                attribute_data = self._attribute_to_dict(attribute)
                attribute_data['createdAt'] = attribute.create_date.isoformat() if attribute.create_date else None
                attribute_data['updatedAt'] = attribute.write_date.isoformat() if attribute.write_date else None
                attribute_data['publishedAt'] = attribute.create_date.isoformat() if attribute.create_date else None
                attributes_data.append(attribute_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_create_variant:
                keyword_meta["filter"]["create_variant"] = filter_create_variant
            if filter_display_type:
                keyword_meta["filter"]["display_type"] = filter_display_type
            
            response = {
                'data': attributes_data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total_count
                    },
                    'keyword': keyword_meta
                }
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({
                'error': 'Error retrieving product variants',
                'message': str(e)
            }, status=500)

    @http.route(f'{BASE_URL}/product', methods=['GET'], auth='public', type="http", cors="*")
    def global_product_list(self, **kw):
        """
        Retrieve a paginated list of all products (global, not shop-specific) with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/product

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for product name, code, or description.
            sort (str, optional): Sort field (id, name, list_price, create_date). Default: name.
            order (str, optional): Sort order (asc, desc). Default: asc.
            filter_category (int, optional): Filter by category ID.
            filter_price_min (float, optional): Minimum price filter.
            filter_price_max (float, optional): Maximum price filter.
            filter_has_variants (bool, optional): Filter products with/without variants.
            filter_shop (int, optional): Filter by shop ID.

        Returns:
            200: Paginated list of all products.
            500: On server error.

        Example Response:
            {
                "data": [
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
                        },
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "coffee",
                        "sort": "list_price",
                        "order": "desc",
                        "filter": {
                            "category": 1,
                            "price_min": 10.0,
                            "price_max": 100.0,
                            "has_variants": true,
                            "shop": 5
                        }
                    }
                }
            }
        """
        try:
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'name')
            order = request.httprequest.args.get('order', 'asc').lower()
            filter_category = request.httprequest.args.get('filter_category', '').strip()
            filter_price_min = request.httprequest.args.get('filter_price_min', '').strip()
            filter_price_max = request.httprequest.args.get('filter_price_max', '').strip()
            filter_has_variants = request.httprequest.args.get('filter_has_variants', '').strip()
            filter_shop = request.httprequest.args.get('filter_shop', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'list_price', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'name'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = []
            
            # Add search functionality
            if search:
                search_domain = [
                    '|', '|',
                    ('name', 'ilike', search),
                    ('default_code', 'ilike', search),
                    ('description', 'ilike', search)
                ]
                domain = search_domain
            
            # Add filters
            if filter_category:
                try:
                    category_id = int(filter_category)
                    domain.append(('categ_id', '=', category_id))
                except ValueError:
                    pass
            
            if filter_price_min:
                try:
                    price_min = float(filter_price_min)
                    domain.append(('list_price', '>=', price_min))
                except ValueError:
                    pass
            
            if filter_price_max:
                try:
                    price_max = float(filter_price_max)
                    domain.append(('list_price', '<=', price_max))
                except ValueError:
                    pass
            
            if filter_has_variants:
                if filter_has_variants.lower() == 'true':
                    domain.append(('attribute_line_ids', '!=', False))
                elif filter_has_variants.lower() == 'false':
                    domain.append(('attribute_line_ids', '=', False))
            
            if filter_shop:
                try:
                    shop_id = int(filter_shop)
                    domain.append(('shop_id', '=', shop_id))
                except ValueError:
                    pass
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_count = request.env['product.product'].sudo().search_count(domain)
            page_count = (total_count + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch products
            products = request.env['product.product'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order=order_clause
            )
            
            products_data = []
            for product in products:
                product_data = self._product_to_dict(product)
                product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
                product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
                product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
                products_data.append(product_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_category:
                keyword_meta["filter"]["category"] = int(filter_category)
            if filter_price_min:
                keyword_meta["filter"]["price_min"] = float(filter_price_min)
            if filter_price_max:
                keyword_meta["filter"]["price_max"] = float(filter_price_max)
            if filter_has_variants:
                keyword_meta["filter"]["has_variants"] = filter_has_variants.lower() == 'true'
            if filter_shop:
                keyword_meta["filter"]["shop"] = int(filter_shop)
            
            response = {
                'data': products_data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total_count
                    },
                    'keyword': keyword_meta
                }
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({
                'error': 'Error retrieving products',
                'message': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/sale", methods=['GET'], auth="public", type="http", cors="*")
    def global_sale_order(self, **kw):
        """
        Retrieve a paginated list of all sale orders (global, not user-specific) with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/sale

        Query Parameters:
            page (int, optional): Page number for pagination (default: 1).
            limit (int, optional): Number of items per page (default: 20, max: 100).
            search (str, optional): Search term for order name or customer name.
            sort (str, optional): Sort field (id, name, date_order, amount_total, create_date). Default: date_order.
            order (str, optional): Sort order (asc, desc). Default: desc.
            filter_state (str, optional): Filter by order state (draft, sent, sale, done, cancel).
            filter_date_from (str, optional): Filter orders from date (YYYY-MM-DD).
            filter_date_to (str, optional): Filter orders to date (YYYY-MM-DD).
            filter_amount_min (float, optional): Minimum amount filter.
            filter_amount_max (float, optional): Maximum amount filter.
            filter_customer (int, optional): Filter by customer ID.

        Returns:
            200: Paginated list of all sale orders.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "SO001",
                        "partner_name": "Customer A",
                        "date_order": "2024-01-01",
                        "amount_total": 100.0,
                        "state": "sale",
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "pageSize": 25,
                        "pageCount": 1,
                        "total": 2
                    },
                    "keyword": {
                        "search": "SO001",
                        "sort": "date_order",
                        "order": "desc",
                        "filter": {
                            "state": "sale",
                            "date_from": "2024-01-01",
                            "date_to": "2024-12-31",
                            "amount_min": 50.0,
                            "amount_max": 200.0,
                            "customer": 1
                        }
                    }
                }
            }
        """
        try:
            # Parse query parameters
            page = int(request.httprequest.args.get('page', 1))
            limit = min(int(request.httprequest.args.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'date_order')
            order = request.httprequest.args.get('order', 'desc').lower()
            filter_state = request.httprequest.args.get('filter_state', '').strip()
            filter_date_from = request.httprequest.args.get('filter_date_from', '').strip()
            filter_date_to = request.httprequest.args.get('filter_date_to', '').strip()
            filter_amount_min = request.httprequest.args.get('filter_amount_min', '').strip()
            filter_amount_max = request.httprequest.args.get('filter_amount_max', '').strip()
            filter_customer = request.httprequest.args.get('filter_customer', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'date_order', 'amount_total', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'date_order'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'desc'
            
            # Build domain
            domain = []
            
            # Add search functionality
            if search:
                search_domain = [
                    '|',
                    ('name', 'ilike', search),
                    ('partner_id.name', 'ilike', search)
                ]
                domain = search_domain
            
            # Add filters
            if filter_state:
                valid_states = ['draft', 'sent', 'sale', 'done', 'cancel']
                if filter_state in valid_states:
                    domain.append(('state', '=', filter_state))
            
            if filter_date_from:
                try:
                    from datetime import datetime
                    date_from = datetime.strptime(filter_date_from, '%Y-%m-%d').date()
                    domain.append(('date_order', '>=', date_from))
                except ValueError:
                    pass
            
            if filter_date_to:
                try:
                    from datetime import datetime
                    date_to = datetime.strptime(filter_date_to, '%Y-%m-%d').date()
                    domain.append(('date_order', '<=', date_to))
                except ValueError:
                    pass
            
            if filter_amount_min:
                try:
                    amount_min = float(filter_amount_min)
                    domain.append(('amount_total', '>=', amount_min))
                except ValueError:
                    pass
            
            if filter_amount_max:
                try:
                    amount_max = float(filter_amount_max)
                    domain.append(('amount_total', '<=', amount_max))
                except ValueError:
                    pass
            
            if filter_customer:
                try:
                    customer_id = int(filter_customer)
                    domain.append(('partner_id', '=', customer_id))
                except ValueError:
                    pass
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_count = request.env['sale.order'].sudo().search_count(domain)
            page_count = (total_count + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch orders
            orders = request.env['sale.order'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order=order_clause
            )
            
            orders_data = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'name': order.name,
                    'partner_name': order.partner_id.name,
                    'date_order': order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
                    'amount_total': order.amount_total,
                    'state': order.state,
                    'createdAt': order.create_date.isoformat() if order.create_date else None,
                    'updatedAt': order.write_date.isoformat() if order.write_date else None,
                    'publishedAt': order.create_date.isoformat() if order.create_date else None
                }
                orders_data.append(order_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_state:
                keyword_meta["filter"]["state"] = filter_state
            if filter_date_from:
                keyword_meta["filter"]["date_from"] = filter_date_from
            if filter_date_to:
                keyword_meta["filter"]["date_to"] = filter_date_to
            if filter_amount_min:
                keyword_meta["filter"]["amount_min"] = float(filter_amount_min)
            if filter_amount_max:
                keyword_meta["filter"]["amount_max"] = float(filter_amount_max)
            if filter_customer:
                keyword_meta["filter"]["customer"] = int(filter_customer)
            
            response = {
                'data': orders_data,
                'meta': {
                    'pagination': {
                        'page': page,
                        'pageSize': limit,
                        'pageCount': page_count,
                        'total': total_count
                    },
                    'keyword': keyword_meta
                }
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({
                'error': 'Error retrieving sale orders',
                'message': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/order", auth="angkit", type="http", methods=["POST"], cors="*", csrf=False)
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:variant_id>/value", type="http", auth="angkit", methods=["GET"], cors="*", csrf=False)
    def variant_value_list(self, shop_id, variant_id, **kw):
        """
        Retrieve all values for a specific product variant in a shop with search and sort capabilities.

        Route: GET /angkort/api/v1/shop/<shop_id>/product/<variant_id>/value

        Parameters:
            shop_id (int): The ID of the shop.
            variant_id (int): The ID of the variant.

        Query Parameters:
            search (str, optional): Search term for value name.
            sort (str, optional): Sort field (id, name, price_extra, create_date). Default: id.
            order (str, optional): Sort order (asc, desc). Default: asc.

        Returns:
            200: List of variant values.
            404: If the shop or attribute is not found.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Red",
                        "extra_price": 5.0,
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "keyword": {
                        "search": "red",
                        "sort": "name",
                        "order": "asc"
                    }
                }
            }
        """
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return Response(json.dumps({'error': 'Attribute not found'}), status=404, content_type='application/json')
            
            # Parse query parameters
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'id')
            order = request.httprequest.args.get('order', 'asc').lower()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'price_extra', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'id'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = [('attribute_id', '=', variant_id)]
            
            # Add search functionality
            if search:
                domain.append(('name', 'ilike', search))
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch values
            values = request.env['product.attribute.value'].sudo().search(
                domain,
                order=order_clause
            )
            
            value_list = []
            for value in values:
                value_data = {
                    'id': value.id,
                    'name': value.name,
                    'extra_price': value.price_extra,
                    'createdAt': value.create_date.isoformat() if value.create_date else None,
                    'updatedAt': value.write_date.isoformat() if value.write_date else None,
                    'publishedAt': value.create_date.isoformat() if value.create_date else None
                }
                value_list.append(value_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order
            }
            
            response = {
                'data': value_list,
                'meta': {
                    'keyword': keyword_meta
                }
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value", type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def variant_value_create(self, shop_id, **kw):
        """
        Create new variant values for a product attribute.

        Route: POST /angkort/api/v1/shop/<shop_id>/product/variant/value

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            attribute_id (int): The ID of the attribute (required).
            values (str): JSON string of values array (required).

        Returns:
            201: Success message.
            400: If required fields are missing or invalid.
            404: If the attribute is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            if 'attribute_id' not in data or 'values' not in data:
                errors = []
                if 'attribute_id' not in data:
                    errors.append({"name": "attribute_id", "message": "Attribute ID is required"})
                if 'values' not in data:
                    errors.append({"name": "values", "message": "Values are required"})
                
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "400",
                    "errors": errors
                }), status=400, content_type='application/json')
            
            attribute = request.env['product.attribute'].sudo().browse(int(data['attribute_id']))
            if not attribute.exists():
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "404",
                    "errors": [{"name": "attribute_id", "message": f"Attribute with ID {data['attribute_id']} not found"}]
                }), status=404, content_type='application/json')
            
            if attribute.shop_id.id != shop_id:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "400",
                    "errors": [{"name": "attribute_id", "message": "Attribute doesn't belong to this shop"}]
                }), status=400, content_type='application/json')
            
            try:
                values_data = json.loads(data['values'])
                if not isinstance(values_data, list):
                    return Response(json.dumps({
                        "status": "error",
                        "message": "Failed to create variant values",
                        "statusCode": "400",
                        "errors": [{"name": "values", "message": "Values must be a list"}]
                    }), status=400, content_type='application/json')
                
                values_to_create = [{
                    'default_extra_price': value.get('extra_price', 0.0),
                    'name': value['name'],
                    'attribute_id': attribute.id,
                } for value in values_data if 'name' in value]
                request.env['product.attribute.value'].sudo().create(values_to_create)
                return Response(json.dumps({'message': 'Attribute values created successfully'}), status=201, content_type='application/json')
            except json.JSONDecodeError:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "400",
                    "errors": [{"name": "values", "message": "Invalid JSON format for values"}]
                }), status=400, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create variant values",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["PUT"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant_value')
    def variant_value_update(self, shop_id, value_id, **kw):
        """
        Update an existing variant value.

        Route: PUT /angkort/api/v1/shop/<shop_id>/product/variant/value/<value_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            value_id (int): The ID of the variant value.
            name (str, optional): New name.
            price_extra (float, optional): New extra price.

        Returns:
            200: Success message.
            400: If no valid fields to update.
            403: If not authorized.
            404: If the variant value is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update variant value",
                    "statusCode": "404",
                    "errors": [{"name": "value_id", "message": "Variant value not found"}]
                }), status=404, content_type='application/json')
            

            
            update_fields = {k: v for k, v in data.items() if k in ['name', 'price_extra']}
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update variant value",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            
            variant_value.write(update_fields)
            return Response(json.dumps({'message': 'Variant value updated successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update variant value",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["PATCH"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant_value')
    def variant_value_patch(self, shop_id, value_id, **kw):
        """
        Partially update an existing variant value.

        Route: PATCH /angkort/api/v1/shop/<shop_id>/product/variant/value/<value_id>

        Parameters (form-data):
            shop_id (int): The ID of the shop.
            value_id (int): The ID of the variant value.
            name (str, optional): New name.
            price_extra (float, optional): New extra price.

        Returns:
            200: Success message.
            400: If no valid fields to update.
            403: If not authorized.
            404: If the variant value is not found.
            500: On server error.
        """
        try:
            data = request.httprequest.form
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch variant value",
                    "statusCode": "404",
                    "errors": [{"name": "value_id", "message": "Variant value not found"}]
                }), status=404, content_type='application/json')
            

            
            update_fields = {k: v for k, v in data.items() if k in ['name', 'price_extra']}
            if not update_fields:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch variant value",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }), status=400, content_type='application/json')
            
            variant_value.write(update_fields)
            return Response(json.dumps({'message': 'Variant value patched successfully'}), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to patch variant value",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant_value')
    def variant_value_delete(self, shop_id, value_id, **kw):
        """
        Delete a variant value.

        Route: DELETE /angkort/api/v1/shop/<shop_id>/product/variant/value/<value_id>

        Parameters:
            shop_id (int): The ID of the shop.
            value_id (int): The ID of the variant value.

        Returns:
            204: On successful deletion.
            403: If not authorized.
            404: If the variant value is not found.
            500: On server error.
        """
        try:
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete variant value",
                    "statusCode": "404",
                    "errors": [{"name": "value_id", "message": "Variant value not found"}]
                }), status=404, content_type='application/json')
            

            
            variant_value.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete variant value",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    # --- SHOP-SPECIFIC PRODUCT VARIANT ROUTES ---
    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["GET"], cors="*", csrf=False)
    def variant_list(self, shop_id, **kw):
        """
        Retrieve all product variants for a specific shop with search, filter, and sort capabilities.

        Route: GET /angkort/api/v1/shop/<shop_id>/product/variant

        Parameters:
            shop_id (int): The ID of the shop.

        Query Parameters:
            search (str, optional): Search term for variant name.
            sort (str, optional): Sort field (id, name, create_date). Default: id.
            order (str, optional): Sort order (asc, desc). Default: asc.
            filter_create_variant (str, optional): Filter by create_variant type (no_variant, always).
            filter_display_type (str, optional): Filter by display_type (multi, radio).

        Returns:
            200: List of product variants for the shop.
            404: If the shop is not found.
            500: On server error.

        Example Response:
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Color",
                        "create_variant": "always",
                        "display_type": "radio",
                        "createdAt": "2024-03-06T13:42:05.098Z",
                        "updatedAt": "2024-03-06T13:42:05.098Z",
                        "publishedAt": "2024-03-06T13:42:05.103Z"
                    }
                ],
                "meta": {
                    "keyword": {
                        "search": "color",
                        "sort": "name",
                        "order": "asc",
                        "filter": {
                            "create_variant": "always",
                            "display_type": "radio"
                        }
                    }
                }
            }
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')
            
            # Parse query parameters
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'id')
            order = request.httprequest.args.get('order', 'asc').lower()
            filter_create_variant = request.httprequest.args.get('filter_create_variant', '').strip()
            filter_display_type = request.httprequest.args.get('filter_display_type', '').strip()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'create_date'}
            if sort not in valid_sort_fields:
                sort = 'id'
            
            # Validate order
            if order not in {'asc', 'desc'}:
                order = 'asc'
            
            # Build domain
            domain = [
                ('create_uid', '=', request.env.user.id),
                ('shop_id', '=', shop_id)
            ]
            
            # Add search functionality
            if search:
                domain.append(('name', 'ilike', search))
            
            # Add filters
            if filter_create_variant:
                if filter_create_variant in ['no_variant', 'always']:
                    domain.append(('create_variant', '=', filter_create_variant))
            
            if filter_display_type:
                if filter_display_type in ['multi', 'radio']:
                    domain.append(('display_type', '=', filter_display_type))
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch attributes
            attributes = request.env['product.attribute'].sudo().search(
                domain,
                order=order_clause
            )
            
            data = []
            for attribute in attributes:
                attribute_data = self._attribute_to_dict(attribute)
                attribute_data['createdAt'] = attribute.create_date.isoformat() if attribute.create_date else None
                attribute_data['updatedAt'] = attribute.write_date.isoformat() if attribute.write_date else None
                attribute_data['publishedAt'] = attribute.create_date.isoformat() if attribute.create_date else None
                data.append(attribute_data)
            
            # Build keyword metadata
            keyword_meta = {
                "search": search if search else None,
                "sort": sort,
                "order": order,
                "filter": {}
            }
            
            if filter_create_variant:
                keyword_meta["filter"]["create_variant"] = filter_create_variant
            if filter_display_type:
                keyword_meta["filter"]["display_type"] = filter_display_type
            
            response = {
                'data': data,
                'meta': {
                    'keyword': keyword_meta
                }
            }
            return Response(json.dumps(response), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
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
                errors = []
                for field in missing_fields:
                    if field == 'name':
                        errors.append({"name": "name", "message": "Variant name is required"})
                    elif field == 'create_variant':
                        errors.append({"name": "create_variant", "message": "Create variant type is required"})
                    elif field == 'display_type':
                        errors.append({"name": "display_type", "message": "Display type is required"})
                
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": errors
                }), status=400, content_type='application/json')
            
            if data['create_variant'] not in VALID_CREATE_VARIANTS:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": [{"name": "create_variant", "message": f"Invalid create_variant value. Must be one of: {', '.join(VALID_CREATE_VARIANTS)}"}]
                }), status=400, content_type='application/json')
            
            if data['display_type'] not in VALID_DISPLAY_TYPES:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": [{"name": "display_type", "message": f"Invalid display_type value. Must be one of: {', '.join(VALID_DISPLAY_TYPES)}"}]
                }), status=400, content_type='application/json')
            
            if request.env['product.attribute'].sudo().search_count([('name', '=', data['name']), ('shop_id', '=', shop_id)], limit=1):
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": [{"name": "name", "message": f"Attribute with name {data['name']} already exists"}]
                }), status=400, content_type='application/json')
            
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
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to create variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PUT"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "404",
                    "errors": [{"name": "variant_id", "message": "Attribute not found"}]
                }), status=404, content_type='application/json')
            
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}
            
            if 'create_variant' in data and data['create_variant'] not in VALID_CREATE_VARIANTS:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "400",
                    "errors": [{"name": "create_variant", "message": f"Invalid create_variant value. Must be one of: {', '.join(VALID_CREATE_VARIANTS)}"}]
                }), status=400, content_type='application/json')
            
            if 'display_type' in data and data['display_type'] not in VALID_DISPLAY_TYPES:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "400",
                    "errors": [{"name": "display_type", "message": f"Invalid display_type value. Must be one of: {', '.join(VALID_DISPLAY_TYPES)}"}]
                }), status=400, content_type='application/json')
            
            if 'name' in data and data['name'] != attribute.name:
                if request.env['product.attribute'].sudo().search_count([('shop_id', '=', shop_id), ('name', '=', data['name'])], limit=1):
                    return Response(json.dumps({
                        "status": "error",
                        "message": "Failed to update variant",
                        "statusCode": "400",
                        "errors": [{"name": "name", "message": f"Attribute with name {data['name']} already exists"}]
                    }), status=400, content_type='application/json')
            
            if data.get('display_type') == 'multi':
                data['create_variant'] = 'no_variant'
            attribute.write(data)
            return Response(json.dumps(self._attribute_to_dict(attribute)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to update variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PATCH"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "404",
                    "errors": [{"name": "variant_id", "message": "Attribute not found"}]
                }), status=404, content_type='application/json')
            
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}
            
            if 'create_variant' in data and data['create_variant'] not in VALID_CREATE_VARIANTS:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "400",
                    "errors": [{"name": "create_variant", "message": f"Invalid create_variant value. Must be one of: {', '.join(VALID_CREATE_VARIANTS)}"}]
                }), status=400, content_type='application/json')
            
            if 'display_type' in data and data['display_type'] not in VALID_DISPLAY_TYPES:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "400",
                    "errors": [{"name": "display_type", "message": f"Invalid display_type value. Must be one of: {', '.join(VALID_DISPLAY_TYPES)}"}]
                }), status=400, content_type='application/json')
            
            if 'name' in data and data['name'] != attribute.name:
                if request.env['product.attribute'].sudo().search_count([('shop_id', '=', shop_id), ('name', '=', data['name'])], limit=1):
                    return Response(json.dumps({
                        "status": "error",
                        "message": "Failed to patch variant",
                        "statusCode": "400",
                        "errors": [{"name": "name", "message": f"Attribute with name {data['name']} already exists"}]
                    }), status=400, content_type='application/json')
            
            if data.get('display_type') == 'multi':
                data['create_variant'] = 'no_variant'
            attribute.write(data)
            return Response(json.dumps(self._attribute_to_dict(attribute)), status=200, content_type='application/json')
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to patch variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant')
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
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete variant",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }), status=404, content_type='application/json')
            
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', variant_id),
                ('shop_id', '=', shop_id),
                ('create_uid', '=', request.env.user.id)
            ], limit=1)
            if not attribute:
                return Response(json.dumps({
                    "status": "error",
                    "message": "Failed to delete variant",
                    "statusCode": "404",
                    "errors": [{"name": "variant_id", "message": "Attribute not found"}]
                }), status=404, content_type='application/json')
            
            attribute.unlink()
            return Response(status=204)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": "Failed to delete variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }), status=500, content_type='application/json')
