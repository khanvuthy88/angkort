import base64
import json
import re
import uuid
import hmac
import hashlib
from urllib.parse import parse_qsl
from datetime import datetime, timedelta
from functools import wraps
from typing import List
import requests
from odoo import http, Command, fields, _
from odoo.http import request
from odoo.tools import config, html2plaintext
from collections import defaultdict
from werkzeug.exceptions import NotFound, BadRequest

# Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_TIMEOUT = 10
 
SALE_STATE = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'sale': 'Sale Order',
    'cancel': 'Cancelled'
}

PARTNER_FIELDS = [
    'name', 'wifi_name', 'phone', 'customer_address', 'shop_latitude', 'shop_longitude', 'email',
    'shop_banner', 'shop_wifi_ids', 'shop_open_hour_ids'
]

ORDER_STATE = {
    'draft': 'Quotation',
    'sent': 'Quotation Sent',
    'sale': 'Sale Order',
    'cancel': 'Cancelled'
}

BASE_URL = '/angkort/api/v1'


def get_current_user_shop_ids(user=None):
    """Return store IDs owned by the current authenticated user.

    We cannot rely on create_uid because many API writes use sudo(), which stamps
    records with the superuser. We therefore prefer the explicit owner field and
    keep a couple of fallbacks for older data.
    """
    current_user = user or request.env.user
    if not current_user or current_user.id == request.env.ref('base.public_user').id:
        return []

    shop_env = request.env['res.partner'].sudo()
    shop_ids = set(shop_env.search([
        ('type', '=', 'store'),
        ('owner_user_id', '=', current_user.id),
    ]).ids)
    shop_ids.update(shop_env.search([
        ('type', '=', 'store'),
        ('create_uid', '=', current_user.id),
    ]).ids)

    parent_shop = current_user.partner_id.parent_id
    if parent_shop and parent_shop.type == 'store':
        shop_ids.add(parent_shop.id)

    return list(shop_ids)


def current_user_owns_shop(shop, user=None):
    """Check whether the current request user owns the provided shop record."""
    return bool(shop and shop.id in set(get_current_user_shop_ids(user=user)))

# Decorators
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
        entity_type (str): Type of entity to check ('shop', 'product', 'category', 'variant', 'variant_value', 'wifi', 'open_hour', 'bank')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
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
                    
                    if not current_user_owns_shop(shop):
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
                    
                    if not current_user_owns_shop(product.shop_id):
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
                    
                    if not current_user_owns_shop(category.shop_id):
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

                    if not current_user_owns_shop(variant.shop_id):
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

                    # Ownership is checked via the parent attribute's shop_id.
                    # Values are created with sudo() so create_uid is always superuser — not usable for ownership.
                    # Also reject values whose parent attribute has no shop_id (global attributes are not shop-owned).
                    attr_shop = variant_value.attribute_id.shop_id
                    if not attr_shop or attr_shop.id != shop_id:
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only modify variant values you own'
                        }, status=403)

                    # Additionally verify the shop itself is owned by the current user
                    attr_shop_record = request.env['res.partner'].sudo().search([
                        ('id', '=', shop_id),
                        ('type', '=', 'store')
                    ], limit=1)
                    if not attr_shop_record or not current_user_owns_shop(attr_shop_record):
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
                        
                        if not current_user_owns_shop(shop):
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
                        
                        if not current_user_owns_shop(wifi.shop_id):
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
                        
                        if not current_user_owns_shop(shop):
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
                        
                        if not current_user_owns_shop(open_hour.shop_id):
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only modify open hours you own'
                            }, status=403)

                elif entity_type == 'bank':
                    shop_id = kwargs.get('shop_id')
                    bank_id = kwargs.get('bank_id')

                    if not shop_id:
                        return request.make_json_response({'error': 'Shop ID is required'}, status=400)

                    # For bank creation, check shop ownership
                    if not bank_id:
                        shop = request.env['res.partner'].sudo().search([
                            ('id', '=', shop_id),
                            ('type', '=', 'store')
                        ], limit=1)

                        if not shop:
                            return request.make_json_response({'error': 'Shop not found'}, status=404)

                        if not current_user_owns_shop(shop):
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only create banks for shops you own'
                            }, status=403)
                    else:
                        # For bank update/delete, check bank ownership
                        bank = request.env['angkort.shop.bank'].sudo().search([
                            ('id', '=', bank_id),
                            ('shop_id', '=', shop_id)
                        ], limit=1)

                        if not bank:
                            return request.make_json_response({'error': 'Bank not found'}, status=404)

                        if not current_user_owns_shop(bank.shop_id):
                            return request.make_json_response({
                                'error': 'Unauthorized: You can only modify banks you own'
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
                    
                    if not current_user_owns_shop(shop):
                        return request.make_json_response({
                            'error': 'Unauthorized: You can only update banners for shops you own'
                        }, status=403)
                
                return func(*args, **kwargs)
                
            except Exception as e:
                return request.make_json_response({'error': f'Authorization check failed: {str(e)}'}, status=500)
        
        return wrapper
    return decorator

class APIUtilsMixin:
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
    def _get_image_url(cls, model_name, record_id, field_name):
        """Generate image URL for Odoo image fields instead of returning base64 data."""
        if record_id and field_name:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            return f'{base_url}/web/image/{model_name}/{record_id}/{field_name}'
        return ''

    @classmethod
    def _product_to_dict(cls, product):
        return {
            'id': product.id,
            'name': product.name,
            'code': product.default_code or '',
            'description': html2plaintext(product.description) if product.description else '',
            'sale_price': product.list_price,
            'image': cls._get_image_url('product.template', product.id, 'image_1920') if product.image_1920 else '',
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
            'id': bank.id,
            'name': bank.name or '',
            'code': bank.code or '',
            'link': bank.link or '',
            'currency': bank.currency or '',
            'logo': cls._get_image_url('angkort.shop.bank', bank.id, 'logo') if bank.logo else '',\
            'shop_id': bank.shop_id.id if bank.shop_id else None
        }

    @classmethod
    def _get_product_details(cls, product):
        product_data = cls._product_to_dict(product)
        # Detailed attribute lines for editing
        product_data['attribute_line_ids'] = [{
            'id': line.id,
            'attribute_id': line.attribute_id.id,
            'attribute_name': line.attribute_id.name,
            'display_type': line.attribute_id.display_type,
            'value_ids': line.value_ids.ids,
            'values': [{
                'id': v.id,
                'name': v.name,
                'html_color': v.html_color
            } for v in line.value_ids]
        } for line in product.attribute_line_ids]
        
        # Legacy fields for frontend compatibility
        product_data['options'] = [cls._get_product_options(option) for option in product.attribute_line_ids.filtered(
            lambda x: x.attribute_id.display_type in ['radio', 'select', 'color'])]
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
            'id': option.id,                           # product.template.attribute.line.id
            'attribute_id': option.attribute_id.id,    # product.attribute.id (for CRUD)
            'name': option.attribute_id.name,          # attribute name (reliable, no prefix)
            'data': [{
                'id': data.product_attribute_value_id.id,  # product.attribute.value.id (for CRUD)
                'name': data.name,
                'price': data.price_extra
            } for data in option.product_template_value_ids]
        }

    @classmethod
    def _get_product_choices(cls, choice):
        return {
            'id': choice.id,
            'attribute_id': choice.attribute_id.id,
            'name': choice.attribute_id.name,
            'data': [{
                'id': data.product_attribute_value_id.id,
                'name': data.name,
                'price': data.price_extra
            } for data in choice.product_template_value_ids]
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

    def _handle_shop_related_fields(self, data, files, operation='create'):
        """
        Helper method to handle shop related fields (shop_banner, shop_wifi_ids, shop_open_hour_ids)
        """
        processed_fields = {}
        
        # Handle banner file upload (Image field expects base64 string)
        banner_file = files.get('shop_banner')
        if banner_file:
            try:
                content = banner_file.read()
                if content:
                    processed_fields['shop_banner'] = base64.b64encode(content).decode('utf-8')
            except Exception:
                # ignore banner if something goes wrong reading it
                pass

        # Helper to parse possible JSON payload passed as string
        def _parse_json_field(val):
            if not val:
                return None
            if isinstance(val, (list, tuple)):
                return val
            try:
                return json.loads(val)
            except Exception:
                return None

        # shop_wifi_ids: accept JSON array and convert to One2many commands
        wifi_payload = data.get('shop_wifi_ids')
        wifi_list = _parse_json_field(wifi_payload)
        if wifi_list:
            wifi_commands = []
            for wifi in wifi_list:
                if not isinstance(wifi, dict):
                    continue
                name = wifi.get('name')
                password = wifi.get('password')
                if not name or not password:
                    continue
                wifi_commands.append((0, 0, {'name': name, 'password': password}))
            if wifi_commands:
                if operation == 'update':
                    # For updates, replace all existing records
                    processed_fields['shop_wifi_ids'] = [(5, 0, 0)] + wifi_commands
                else:
                    # For create, just add new records
                    processed_fields['shop_wifi_ids'] = wifi_commands

        # shop_open_hour_ids: accept JSON array and convert to One2many commands
        hour_payload = data.get('shop_open_hour_ids')
        hour_list = _parse_json_field(hour_payload)
        if hour_list:
            hour_commands = []
            for hour in hour_list:
                if not isinstance(hour, dict):
                    continue
                day = hour.get('day')
                open_time = hour.get('open')
                close_time = hour.get('close')
                if day is None:
                    continue
                # ensure day is stored as string (model expects selection string values like '0','1',...)
                hour_commands.append((0, 0, {'day': str(day), 'open': open_time, 'close': close_time}))
            if hour_commands:
                if operation == 'update':
                    # For updates, replace all existing records
                    processed_fields['shop_open_hour_ids'] = [(5, 0, 0)] + hour_commands
                else:
                    # For create, just add new records
                    processed_fields['shop_open_hour_ids'] = hour_commands
                    
        return processed_fields

    @classmethod
    def verify_telegram_init_data(cls, init_data, bot_token):
        """
        Verifies the integrity of the data received from Telegram Mini App.
        """
        try:
            if not bot_token:
                return False, "Bot token not configured"
                
            parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
            if 'hash' not in parsed_data:
                return False, "Hash missing in init_data"
                
            received_hash = parsed_data.pop('hash')
            
            # Data-check-string is a chain of all received fields, sorted alphabetically
            data_check_arr = []
            for key in sorted(parsed_data.keys()):
                data_check_arr.append(f'{key}={parsed_data[key]}')
            data_check_string = '\n'.join(data_check_arr)
            
            # Secret key is the HMAC-SHA256 of the bot token using "WebAppData" as key
            secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
            
            # Hash is the HMAC-SHA256 of the data_check_string using the secret_key
            computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            
            if computed_hash != received_hash:
                return False, "Invalid hash"
                
            # Check auth_date for replay attacks (e.g. 24 hours validity)
            if 'auth_date' in parsed_data:
                auth_date = int(parsed_data['auth_date'])
                if (datetime.now().timestamp() - auth_date) > 86400:
                    return False, "Data is outdated"
                 
            return True, "Valid"
        except Exception as e:
            return False, str(e)


class BaseAPIController(http.Controller, APIUtilsMixin):
    """
    Base controller providing standardized response and logic helpers for all Angkort API routes.
    """
    
    def success_response(self, data, meta=None, status=200):
        """Returns a standardized successful JSON response."""
        response = {'status': 'success', 'data': data}
        if meta:
            response['meta'] = meta
        return request.make_json_response(response, status=status)

    def error_response(self, message, status=500, errors=None, traceback=None):
        """Returns a standardized error JSON response."""
        response = {
            'status': 'error',
            'message': message,
            'statusCode': status
        }
        if errors:
            response['errors'] = errors
        if traceback:
            response['traceback'] = traceback
        return request.make_json_response(response, status=status)

    def _paginate(self, model_name, domain, page=1, limit=DEFAULT_PAGE_SIZE, order='id desc'):
        """Helper to search and paginate records."""
        model = request.env[model_name].sudo()
        total = model.search_count(domain)
        page_count = (total + limit - 1) // limit
        
        records = model.search(
            domain,
            offset=(page - 1) * limit,
            limit=limit,
            order=order
        )
        
        meta = {
            'pagination': {
                'page': page,
                'pageSize': limit,
                'pageCount': page_count,
                'total': total
            }
        }
        return records, meta

    def _get_my_shop_ids(self):
        """Get IDs of shops owned by the current user."""
        return get_current_user_shop_ids()
