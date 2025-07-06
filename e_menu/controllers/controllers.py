# -*- coding: utf-8 -*-
import base64
import json
import re
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Union, Any

import requests
from werkzeug.exceptions import NotFound, BadRequest

import odoo
from odoo import http, tools
from odoo.api import call_kw
from odoo.models import check_method_name
from odoo.tools import config
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo import fields, _

from odoo.tools.mimetypes import guess_mimetype

# Constants
BASE_URL = '/angkort/api/v1'
SAVE_IMAGE_URL = "/html_editor/attachment/add_data"
SALE_STATE = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'sale': 'Sale Order',
    'cancel': 'Cancelled'
}

SUPPORTED_IMAGE_MIMETYPES = {
    'image/gif': '.gif',
    'image/jpe': '.jpe',
    'image/jpeg': '.jpeg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/svg+xml': '.svg',
    'image/webp': '.webp',
}

PARTNER_FIELDS = [
    'name', 'wifi_name', 'phone', 'customer_address', 'shop_latitude', 'shop_longitude', 'email'
]

# Performance constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_TIMEOUT = 10


def validate_auth(func):
    """Decorator to validate authentication for protected endpoints."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check if user is authenticated
            if not request.env.user or request.env.user.id == request.env.ref('base.public_user').id:
                return request.make_json_response({'error': 'Authentication required'}, status=401)
            return func(*args, **kwargs)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)
    return wrapper


def validate_input_data(required_fields: List[str] = None, optional_fields: List[str] = None):
    """Decorator to validate input data for endpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Handle both JSON and form data
                if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                    data = request.get_json_data()
                else:
                    # For form data, get from request params
                    data = dict(request.params)
                
                if not data:
                    return request.make_json_response({'error': 'No data provided'}, status=400)
                
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return request.make_json_response({
                            'error': f'Missing required fields: {", ".join(missing_fields)}'
                        }, status=400)
                
                if optional_fields:
                    # Validate that all provided fields are either required or optional
                    all_valid_fields = set(required_fields or []) | set(optional_fields or [])
                    invalid_fields = [field for field in data.keys() if field not in all_valid_fields]
                    if invalid_fields:
                        return request.make_json_response({
                            'error': f'Invalid fields: {", ".join(invalid_fields)}'
                        }, status=400)
                
                return func(*args, **kwargs)
            except Exception as e:
                return request.make_json_response({'error': str(e)}, status=500)
        return wrapper
    return decorator


def paginate_results(func):
    """Decorator to add pagination to list endpoints."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get pagination parameters from query string for HTTP requests
            page = int(request.params.get('page', 1))
            limit = min(int(request.params.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            
            if page < 1:
                return request.make_json_response({'error': 'Page number must be positive'}, status=400)
            
            # Add pagination to kwargs
            kwargs['page'] = page
            kwargs['limit'] = limit
            kwargs['offset'] = (page - 1) * limit
            
            return func(*args, **kwargs)
        except ValueError:
            return request.make_json_response({'error': 'Invalid pagination parameters'}, status=400)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)
    return wrapper


class EMenu(http.Controller):
    """Enhanced EMenu controller with improved error handling and performance optimizations."""

    def _clean_context(self):
        """Clean context to avoid company restrictions."""
        context = dict(request.context)
        context.pop('allowed_company_ids', None)
        request.update_env(context=context)

    def _image_to_webp(self, attachment, res_model=None, res_id=None, name=None, data=None, original_id=None,
                       mimetype=None, alt_data=None):
        """
        Creates a modified copy of an attachment and returns its image_src to be
        inserted into the DOM.
        """
        try:
            self._clean_context()
            attachment = request.env['ir.attachment'].browse(attachment.id)
            
            fields = {
                'original_id': attachment.id,
                'datas': data,
                'type': 'binary',
                'res_model': res_model or 'ir.ui.view',
                'mimetype': mimetype or attachment.mimetype,
                'name': name or attachment.name,
            }
            
            if fields['res_model'] == 'ir.ui.view':
                fields['res_id'] = 0
            elif res_id:
                fields['res_id'] = res_id
                
            if fields['mimetype'] == 'image/webp':
                fields['name'] = re.sub(r'\.(jpe?g|png)$', '.webp', fields['name'], flags=re.I)
                
            attachment = attachment.copy(fields)
            
            if alt_data:
                for size, per_type in alt_data.items():
                    reference_id = attachment.id
                    if 'image/webp' in per_type:
                        resized = attachment.create_unique([{
                            'name': attachment.name,
                            'description': 'resize: %s' % size,
                            'datas': per_type['image/webp'],
                            'res_id': reference_id,
                            'res_model': 'ir.attachment',
                            'mimetype': 'image/webp',
                        }])
                        reference_id = resized[0]
                    if 'image/jpeg' in per_type:
                        attachment.create_unique([{
                            'name': re.sub(r'\.webp$', '.jpg', attachment.name, flags=re.I),
                            'description': 'format: jpeg',
                            'datas': per_type['image/jpeg'],
                            'res_id': reference_id,
                            'res_model': 'ir.attachment',
                            'mimetype': 'image/jpeg',
                        }])
                        
            if attachment.url:
                if re.match(r'^/\w+/static/', attachment.url):
                    attachment.url = None
                else:
                    url_fragments = attachment.url.split('/')
                    url_fragments.insert(-1, str(attachment.id))
                    attachment.url = '/'.join(url_fragments)
                    
            if attachment.public:
                return attachment.image_src
                
            attachment.generate_access_token()
            return '%s?access_token=%s' % (attachment.image_src, attachment.access_token)
            
        except Exception as e:
            raise UserError(f"Error processing image: {str(e)}")

    def _attachment_create(self, name='', data=False, url=False, res_id=False, res_model='ir.ui.view'):
        """Create and return a new attachment with improved error handling."""
        try:
            IrAttachment = request.env['ir.attachment']

            if name.lower().endswith('.bmp'):
                name = name[:-4]

            if not name and url:
                name = url.split("/").pop()

            if res_model != 'ir.ui.view' and res_id:
                res_id = int(res_id)
            else:
                res_id = False

            attachment_data = {
                'name': name,
                'public': res_model == 'ir.ui.view',
                'res_id': res_id,
                'res_model': res_model,
            }

            if data:
                attachment_data['raw'] = data
                if url:
                    attachment_data['url'] = url
            elif url:
                attachment_data.update({
                    'type': 'url',
                    'url': url,
                })
                
                # Validate URL and get MIME type
                try:
                    response = requests.head(url, timeout=DEFAULT_TIMEOUT)
                    if response.status_code == 200:
                        mime_type = response.headers.get('content-type', '').split(';')[0]
                        if mime_type in SUPPORTED_IMAGE_MIMETYPES:
                            attachment_data['mimetype'] = mime_type
                except requests.RequestException:
                    # Continue without MIME type if HEAD request fails
                    pass
            else:
                raise UserError(_("You need to specify either data or url to create an attachment."))

            # Create attachment with proper permissions
            if (
                    not request.env.is_admin()
                    and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
            ):
                attachment = IrAttachment.sudo().create(attachment_data)
                if not attachment_data['public']:
                    attachment.sudo().generate_access_token()
            else:
                attachment = IrAttachment.create(attachment_data)

            return attachment
            
        except Exception as e:
            raise UserError(f"Error creating attachment: {str(e)}")

    def find_or_create_token(self):
        """Generate or refresh API token with improved error handling."""
        try:
            # Remove existing tokens
            request.env.user.api_key_ids.unlink()
            
            # Generate new token
            key = request.env['res.users.apikeys'].with_user(request.env.user)._generate(
                'rpc', 'angkort', fields.Datetime.now() + timedelta(days=1)
            )
            
            return {
                'state': True, 
                'token_key': key
            }
        except Exception as e:
            return {
                'state': False, 
                'error': str(e)
            }

    def _string_to_string_list(self, string: str) -> List[str]:
        """Convert comma-separated string to list with proper handling."""
        if not string:
            return []
        return [item.strip() for item in string.split(',') if item.strip()]

    def _format_response(self, success: bool, data: Any = None, message: str = None, 
                        status_code: int = 200) -> Dict[str, Any]:
        """Standardized response format."""
        response = {'status': success}
        if data is not None:
            response['data'] = data
        if message is not None:
            response['message'] = message
        return response

    def _handle_exception(self, e: Exception, default_message: str = "An error occurred") -> Dict[str, Any]:
        """Standardized exception handling."""
        error_message = str(e) if str(e) else default_message
        return self._format_response(False, message=error_message)

    def _get_request_data(self):
        """Get request data from either JSON or form data."""
        try:
            if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                return request.get_json_data()
            else:
                # For form data or query parameters
                return dict(request.params)
        except Exception:
            return {}

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", methods=["GET"], auth="public", type="http", cors="*")
    def shop_detail(self, shop_id):
        """
        Get detailed information about a specific shop.
        
        Args:
            shop_id (int): The ID of the shop to retrieve
            
        Returns:
            dict: Shop details including contact info, location, and banking details
        """
        try:
            # Validate shop_id
            if not shop_id or shop_id <= 0:
                return request.make_json_response(
                    self._handle_exception(ValueError("Invalid shop ID"), "Invalid shop ID"), 
                    status=400
                )

            # Get shop with optimized query
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')  # Assuming shops have type 'store'
            ], limit=1)
            
            if not shop:
                return request.make_json_response(
                    self._handle_exception(NotFound("Shop not found"), "Shop not found"), 
                    status=404
                )

            # Prepare response data
            shop_data = {
                'id': shop.id,
                'name': shop.name or '',
                'phoneNumber': self._string_to_string_list(shop.phone),
                'address': [shop.customer_address] if shop.customer_address else [],
                'wifi': self._string_to_string_list(shop.wifi_name),
                'banks': [
                    {
                        'name': bank.name or '',
                        'link': bank.link or '',
                        'currency': bank.currency or '',
                        'logo': bank.logo
                    } for bank in shop.shop_bank_ids
                ]
            }

            return request.make_json_response(
                self._format_response(True, shop_data), 
                status=200
            )
            
        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving shop details"), 
                status=500
            )

    @http.route(f"{BASE_URL}/shop/create", auth="public", type="http", cors="*", methods=["POST"])
    def create_shop(self):
        """
        Create a new shop with validation and error handling.
        
        Returns:
            dict: Created shop information
        """
        try:
            data = self._get_request_data()
            create_data = data.get('params', data)  # Handle both params and direct data
            
            # Validate required fields
            required_fields = ['name', 'phone', 'customer_address']
            missing_fields = [field for field in required_fields if not create_data.get(field)]
            if missing_fields:
                return request.make_json_response(
                    self._handle_exception(ValueError(f"Missing required fields: {', '.join(missing_fields)}")), 
                    status=400
                )

            # Create shop with proper context
            shop_data = request.env['res.partner'].sudo().with_context(
                create_company=True
            ).create([{
                'name': create_data['name'],
                'phone': create_data['phone'],
                'customer_address': create_data['customer_address'],
                'type': 'store',  # Mark as shop
                'wifi_name': create_data.get('wifi_name', ''),
                'shop_latitude': create_data.get('shop_latitude', 0.0),
                'shop_longitude': create_data.get('shop_longitude', 0.0),
                'email': create_data.get('email', ''),
            }])
            
            # Update user's partner relationship if authenticated
            if request.env.user.id != request.env.ref('base.public_user').id:
                request.env.user.partner_id.update({
                    'parent_id': shop_data.id
                })
                
            return request.make_json_response(
                self._format_response(True, {
                    'name': shop_data.name,
                    'id': shop_data.id
                }, "Shop created successfully"), 
                status=201
            )
            
        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error creating shop"), 
                status=500
            )

    @http.route(f"{BASE_URL}/industries", methods=['GET'], auth="public", type="http", cors="*")
    @paginate_results
    def industries(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of all available industries.

        This endpoint returns a JSON response containing industry records sorted alphabetically by name,
        along with pagination metadata. The data includes both the full display name and the short name
        for each industry.

        Args:
            page (int, optional): The current page number for pagination. Defaults to 1.
            limit (int, optional): Maximum number of records to return per page. Defaults to DEFAULT_PAGE_SIZE.
            offset (int, optional): Database query offset for pagination. Defaults to 0.

        Returns:
            dict: JSON response containing:
                - status (bool): Indicates if request was successful
                - data (dict):
                    - industries (list): List of industry dictionaries with:
                        - id (int): Industry database ID
                        - full_name (str): Complete industry name for display
                        - name (str): Short industry name/code
                    - pagination (dict): Pagination metadata including:
                        - total (int): Total number of records
                        - page (int): Current page number
                        - limit (int): Records per page
                        - pages (int): Total number of pages

        Raises:
            HTTPException: Returns 500 status code with error message if any exception occurs

        Example Response:
            {
                "status": true,
                "data": {
                    "industries": [
                        {
                            "id": 1,
                            "full_name": "Information Technology",
                            "name": "IT"
                        },
                        ...
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
            # Get industries with pagination
            industries = request.env['res.partner.industry'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )

            # Get total count for pagination
            total_count = request.env['res.partner.industry'].sudo().search_count([])

            # Prepare response data
            industries_data = [{
                'id': industry.id,
                'full_name': industry.full_name or industry.name,
                'name': industry.name
            } for industry in industries]

            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }

            return request.make_json_response(
                self._format_response(True, {
                    'industries': industries_data,
                    'pagination': pagination_data
                }),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving industries"),
                status=500
            )

    @http.route(f"{BASE_URL}/login", auth="public", type="http", cors="*", methods=["POST"])
    def login(self):
        """
        Authenticate user credentials and generate an API access token.

        This endpoint validates user credentials (username/password) against the database
        and returns an API token for authenticated requests if successful. The token
        can be used for subsequent authenticated API calls.

        Request Body:
            JSON object containing:
                - username (str): User's login name (required)
                - password (str): User's password (required)

        Returns:
            dict: JSON response containing:
                - status (bool): Authentication success status
                - message (str): Result message
                - data (dict): On success contains:
                    - token_key (str): Generated API token
                    - user_id (int): Authenticated user ID
                    - username (str): Authenticated username

        Raises:
            HTTP 400: If required fields are missing
            HTTP 401: If authentication fails (invalid credentials)
            HTTP 500: If token generation fails or server error occurs

        Example Request:
            POST /api/login
            {
                "username": "admin",
                "password": "securepassword123"
            }

        Example Success Response:
            {
                "status": true,
                "message": "Login successful",
                "data": {
                    "token_key": "a1b2c3d4e5f6",
                    "user_id": 1,
                    "username": "admin"
                }
            }

        Example Error Response:
            {
                "status": false,
                "message": "Invalid credentials",
                "error": "Authentication failed"
            }
        """
        try:
            data = self._get_request_data()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return request.make_json_response(
                    self._handle_exception(ValueError("Username and password are required")),
                    status=400
                )

            # Authenticate user
            db = config['db_name']
            credential = {'login': username, 'password': password, 'type': 'password'}

            try:
                uid = request.session.authenticate(db, credential)
                if not uid:
                    return request.make_json_response(
                        self._handle_exception(ValueError("Invalid credentials")),
                        status=401
                    )
            except Exception as auth_error:
                return request.make_json_response(
                    self._handle_exception(auth_error, "Authentication failed"),
                    status=401
                )

            # Generate token
            token_result = self.find_or_create_token()
            if not token_result['state']:
                return request.make_json_response(
                    self._handle_exception(Exception(token_result['error']), "Token generation failed"),
                    status=500
                )

            return request.make_json_response(
                self._format_response(True, {
                    'token_key': token_result['token_key'],
                    'user_id': request.env.user.id,
                    'username': request.env.user.login
                }, "Login successful"),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Login failed"),
                status=500
            )

    @http.route(f"{BASE_URL}/product/category", methods=['GET'], auth="public", type="http", cors="*")
    @paginate_results
    def product_category(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of product categories with hierarchical information.

        This endpoint returns all product categories in alphabetical order, including their
        parent category relationships when they exist. The response includes pagination
        metadata for large result sets.

        Args:
            page (int, optional): The page number to return (1-based index). Defaults to 1.
            limit (int, optional): Maximum number of categories per page. Defaults to DEFAULT_PAGE_SIZE.
            offset (int, optional): Database query offset for pagination. Defaults to 0.

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - data (dict):
                    - categories (list): List of category objects with:
                        - id (int): Category unique identifier
                        - name (str): Category display name
                        - parent_id (int|null): ID of parent category (null if root category)
                        - parent_name (str|null): Name of parent category (null if root category)
                    - pagination (dict): Pagination metadata including:
                        - total (int): Total number of categories
                        - page (int): Current page number
                        - limit (int): Categories per page
                        - pages (int): Total number of pages

        Raises:
            HTTP 500: If server encounters an error while processing the request

        Example Request:
            GET /api/product/category?page=2&limit=20

        Example Success Response:
            {
                "status": true,
                "data": {
                    "categories": [
                        {
                            "id": 15,
                            "name": "Electronics",
                            "parent_id": null,
                            "parent_name": null
                        },
                        {
                            "id": 23,
                            "name": "Smartphones",
                            "parent_id": 15,
                            "parent_name": "Electronics"
                        }
                    ],
                    "pagination": {
                        "total": 42,
                        "page": 2,
                        "limit": 20,
                        "pages": 3
                    }
                }
            }

        Example Error Response:
            {
                "status": false,
                "message": "Error retrieving product categories",
                "error": "Database connection failed"
            }
        """
        try:
            # Get categories with pagination
            categories = request.env['product.category'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )

            # Get total count for pagination
            total_count = request.env['product.category'].sudo().search_count([])

            # Prepare response data
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

            return request.make_json_response(
                self._format_response(True, {
                    'categories': categories_data,
                    'pagination': pagination_data
                }),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving product categories"),
                status=500
            )

    @http.route(f"{BASE_URL}/image/add", auth="public", type="http", methods=["POST"], csrf=False)
    def image_add(self, quality=0, width=0, height=0, res_id=False, res_model='ir.ui.view', **kw):
        """
        Upload, validate, process, and store an image with automatic WebP conversion.

        This endpoint accepts image uploads, validates the format, processes dimensions/quality,
        stores the image as an attachment, and generates a WebP version. Supports common image
        formats including JPEG, PNG, and GIF.

        Args:
            quality (int, optional): Image quality percentage (0-100). 0 preserves original quality.
            width (int, optional): Target width in pixels (0 maintains aspect ratio with height).
            height (int, optional): Target height in pixels (0 maintains aspect ratio with width).
            res_id (int|bool, optional): Related record ID for attachment. Defaults to False.
            res_model (str, optional): Related model name for attachment. Defaults to 'ir.ui.view'.
            **kw: Additional keyword arguments from request.

        Request:
            POST with multipart/form-data containing:
                - image (file): The image file to upload (required)

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - message (str): Result message
                - data (dict):
                    - image (str): URL of the processed WebP image
                    - image_id (int): ID of the created attachment record

        Raises:
            HTTP 400: If no image provided, invalid file, or unsupported format
            HTTP 500: If server error occurs during processing

        Supported Formats:
            JPEG, PNG, GIF, WEBP

        Example Request:
            POST /api/image/add?width=800&quality=85
            Headers:
                Content-Type: multipart/form-data
            Body:
                image: [file data]

        Example Success Response:
            {
                "status": true,
                "message": "Image uploaded successfully",
                "data": {
                    "image": "/web/image/123/800x600/image.webp",
                    "image_id": 123
                }
            }

        Example Error Responses:
            {
                "status": false,
                "message": "No image file provided",
                "error": "Missing required file"
            }
            {
                "status": false,
                "message": "Unsupported image format",
                "error": "Uploaded image's format is not supported. Try with: JPEG, PNG, GIF"
            }
        """
        try:
            # Validate file upload
            if 'image' not in request.httprequest.files:
                return request.make_json_response(
                    self._handle_exception(ValueError("No image file provided")),
                    status=400
                )

            image_file = request.httprequest.files['image']
            if not image_file.filename:
                return request.make_json_response(
                    self._handle_exception(ValueError("Invalid image file")),
                    status=400
                )

            # Read and encode image
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            data = base64.b64decode(image_data)
            format_error_msg = _("Uploaded image's format is not supported. Try with: %s",
                                 ', '.join(SUPPORTED_IMAGE_MIMETYPES.values()))

            # Process image
            try:
                data = tools.image_process(data, size=(width, height), quality=quality, verify_resolution=True)
                mimetype = guess_mimetype(data)

                if mimetype not in SUPPORTED_IMAGE_MIMETYPES:
                    return request.make_json_response(
                        self._handle_exception(ValueError(format_error_msg)),
                        status=400
                    )

                name = f'{image_file.filename}%s-%s%s' % (
                    datetime.now().strftime('%Y%m%d%H%M%S'),
                    str(uuid.uuid4())[:6],
                    SUPPORTED_IMAGE_MIMETYPES[mimetype],
                )
            except UserError:
                return request.make_json_response(
                    self._handle_exception(ValueError(format_error_msg)),
                    status=400
                )
            except ValueError as e:
                return request.make_json_response(
                    self._handle_exception(e),
                    status=400
                )

            # Create attachment and generate webp
            self._clean_context()
            attachment = self._attachment_create(name=name, data=data, res_id=res_id, res_model=res_model)
            image_webp_url = self._image_to_webp(attachment=attachment, mimetype="image/webp", data=attachment.datas)

            return request.make_json_response(
                self._format_response(True, {
                    'image': image_webp_url,
                    'image_id': attachment.id
                }, "Image uploaded successfully"),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error uploading image"),
                status=500
            )

    @http.route(f"{BASE_URL}/product/<int:product_id>", methods=['GET'], auth="public", type="http", cors="*")
    def product_detail(self, product_id):
        """
        Retrieve comprehensive product details including variants, options, and pricing.

        This endpoint returns complete product information including:
        - Basic product details (name, description, pricing)
        - Category information
        - Product options (radio button attributes)
        - Product choices (multi-select attributes)
        - Image URLs
        - Variant pricing differences

        Args:
            product_id (int): The ID of the product to retrieve (from URL path)

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - data (dict):
                    - product_data (dict): Core product information including:
                        - id (int): Product ID
                        - name (str): Product name
                        - description (str): Product description (HTML)
                        - image (str): Base64 encoded main product image
                        - list_price (float): Base product price
                        - default_code (str): Product SKU/reference
                        - category (dict|null): Product category info with:
                            - id (int): Category ID
                            - name (str): Category name
                    - options (list): Radio-type attribute options with:
                        - id (int): Attribute ID
                        - name (str): Attribute display name
                        - data (list): Available values with:
                            - id (int): Value ID
                            - name (str): Value name
                            - price (float): Price adjustment
                    - choices (list): Multi-select attributes with same structure as options

        Raises:
            HTTP 400: If product ID is invalid
            HTTP 404: If product is not found
            HTTP 500: If server error occurs

        Example Request:
            GET /api/product/123

        Example Success Response:
            {
                "status": true,
                "data": {
                    "product_data": {
                        "id": 123,
                        "name": "Premium T-Shirt",
                        "description": "<p>100% Cotton premium t-shirt</p>",
                        "image": "data:image/png;base64,...",
                        "list_price": 29.99,
                        "default_code": "TSH-PRM-01",
                        "category": {
                            "id": 5,
                            "name": "Apparel"
                        }
                    },
                    "options": [
                        {
                            "id": 1,
                            "name": "Size",
                            "data": [
                                {"id": 1, "name": "S", "price": 0},
                                {"id": 2, "name": "M", "price": 0}
                            ]
                        }
                    ],
                    "choices": [
                        {
                            "id": 2,
                            "name": "Colors",
                            "data": [
                                {"id": 3, "name": "Red", "price": 2.50},
                                {"id": 4, "name": "Blue", "price": 0}
                            ]
                        }
                    ]
                }
            }

        Example Error Responses:
            {
                "status": false,
                "message": "Invalid product ID",
                "error": "Product ID must be positive integer"
            }
            {
                "status": false,
                "message": "Product not found",
                "error": "No product exists with ID 999"
            }
        """
        try:
            # Validate product_id
            if not product_id or product_id <= 0:
                return request.make_json_response(
                    self._handle_exception(ValueError("Invalid product ID")),
                    status=400
                )

            # Get product with optimized query
            product = request.env['product.template'].sudo().search([
                ('id', '=', product_id)
            ], limit=1)

            if not product:
                return request.make_json_response(
                    self._handle_exception(NotFound("Product not found")),
                    status=404
                )

            # Prepare response data
            product_data = {
                'id': product.id,
                'name': product.name or '',
                'description': product.description or '',
                'image': product.image_1920 or '',
                'list_price': product.list_price,
                'default_code': product.default_code,
                'category': {
                    'id': product.categ_id.id if product.categ_id else None,
                    'name': product.categ_id.name if product.categ_id else None
                }
            }

            # Get options (radio type attributes)
            options = []
            for option in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'radio'):
                option_data = {
                    'id': option.attribute_id.id,
                    'name': option.attribute_id.display_name,
                    'data': [{
                        'id': value.id,
                        'name': value.name,
                        'price': value.price_extra
                    } for value in option.product_template_value_ids]
                }
                options.append(option_data)

            # Get choices (multi type attributes)
            choices = []
            for choice in product.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'multi'):
                choice_data = {
                    'id': choice.attribute_id.id,
                    'name': choice.attribute_id.display_name,
                    'data': [{
                        'id': value.id,
                        'name': value.name,
                        'price': value.price_extra
                    } for value in choice.product_template_value_ids]
                }
                choices.append(choice_data)

            return request.make_json_response(
                self._format_response(True, {
                    'product_data': product_data,
                    'options': options,
                    'choices': choices
                }),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving product details"),
                status=500
            )

    @http.route(f"{BASE_URL}/product/variant", methods=['GET'], auth="public", type="http", cors="*")
    @paginate_results
    def product_variant(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve paginated list of product variants/attributes with their possible values.

        This endpoint returns all product attributes (like size, color etc.) along with their
        possible values and price adjustments. The results are paginated and sorted alphabetically.

        Args:
            page (int, optional): Page number to return (1-based). Defaults to 1.
            limit (int, optional): Number of records per page. Defaults to DEFAULT_PAGE_SIZE.
            offset (int, optional): Database offset for pagination. Defaults to 0.

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - data (dict):
                    - variants (list): Product attributes with:
                        - id (int): Attribute ID
                        - name (str): Attribute name (e.g., "Color", "Size")
                        - display_type (str): How attribute is displayed ('radio', 'select', 'color')
                        - create_variant (bool): Whether attribute creates actual product variants
                        - values (list): Possible attribute values with:
                            - id (int): Value ID
                            - name (str): Value name (e.g., "Red", "Large")
                            - price_extra (float): Additional price for this value
                    - pagination (dict): Pagination metadata:
                        - total (int): Total number of attributes
                        - page (int): Current page number
                        - limit (int): Records per page
                        - pages (int): Total number of pages

        Raises:
            HTTP 500: If server error occurs during processing

        Example Request:
            GET /api/product/variant?page=2&limit=10

        Example Success Response:
            {
                "status": true,
                "data": {
                    "variants": [
                        {
                            "id": 1,
                            "name": "Color",
                            "display_type": "radio",
                            "create_variant": true,
                            "values": [
                                {"id": 1, "name": "Red", "price_extra": 0.0},
                                {"id": 2, "name": "Blue", "price_extra": 2.5}
                            ]
                        },
                        {
                            "id": 2,
                            "name": "Size",
                            "display_type": "select",
                            "create_variant": true,
                            "values": [
                                {"id": 3, "name": "S", "price_extra": 0.0},
                                {"id": 4, "name": "M", "price_extra": 0.0}
                            ]
                        }
                    ],
                    "pagination": {
                        "total": 15,
                        "page": 2,
                        "limit": 10,
                        "pages": 2
                    }
                }
            }

        Example Error Response:
            {
                "status": false,
                "message": "Error retrieving product variants",
                "error": "Database connection error"
            }
        """
        try:
            # Get product attributes with pagination
            product_variants = request.env['product.attribute'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )

            # Get total count for pagination
            total_count = request.env['product.attribute'].sudo().search_count([])

            # Prepare response data
            variants_data = [{
                'id': variant.id,
                'name': variant.name,
                'display_type': variant.display_type,
                'create_variant': variant.create_variant,
                'values': [{
                    'id': value.id,
                    'name': value.name,
                    'price_extra': value.price_extra
                } for value in variant.value_ids]
            } for variant in product_variants]

            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }

            return request.make_json_response(
                self._format_response(True, {
                    'variants': variants_data,
                    'pagination': pagination_data
                }),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving product variants"),
                status=500
            )

    @http.route(f'{BASE_URL}/product', methods=['GET'], auth='public', type="http", cors="*")
    @paginate_results
    def product_list(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of products with essential details.

        This endpoint returns a paginated list of all available products, including basic
        product information, pricing, and category details. The results are optimized
        for performance and include only essential fields.

        Args:
            page (int, optional): Page number to return (1-based index). Defaults to 1.
            limit (int, optional): Number of products per page. Defaults to DEFAULT_PAGE_SIZE.
            offset (int, optional): Database query offset for pagination. Defaults to 0.

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - data (dict):
                    - products (list): Product objects with:
                        - id (int): Product ID
                        - name (str): Product name
                        - code (str): Product SKU/reference
                        - description (str): Product description (HTML formatted)
                        - sale_price (float): Product sale price
                        - image (str): Base64 encoded product image (512x512px)
                        - category (dict|null): Product category info:
                            - id (int): Category ID
                            - name (str): Category name
                    - pagination (dict): Pagination metadata:
                        - total (int): Total number of products
                        - page (int): Current page number
                        - limit (int): Products per page
                        - pages (int): Total number of pages

        Notes:
            - Results are ordered alphabetically by product name
            - Image is returned as base64 encoded string
            - Category will be null if product has no category assigned

        Raises:
            HTTP 500: If server error occurs during processing

        Example Request:
            GET /api/product?page=2&limit=20

        Example Success Response:
            {
                "status": true,
                "data": {
                    "products": [
                        {
                            "id": 101,
                            "name": "Premium Headphones",
                            "code": "AUD-PH-01",
                            "description": "<p>Noise-cancelling wireless headphones</p>",
                            "sale_price": 199.99,
                            "image": "data:image/png;base64,...",
                            "category": {
                                "id": 5,
                                "name": "Electronics"
                            }
                        },
                        ...
                    ],
                    "pagination": {
                        "total": 150,
                        "page": 2,
                        "limit": 20,
                        "pages": 8
                    }
                }
            }

        Example Error Response:
            {
                "status": false,
                "message": "Error retrieving product list",
                "error": "Database connection timeout"
            }
        """
        try:
            # Get products with pagination and optimized fields
            products = request.env['product.template'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='name'
            )

            # Get total count for pagination
            total_count = request.env['product.template'].sudo().search_count([])

            # Prepare response data with field limiting
            products_data = [{
                'id': product.id,
                'name': product.name,
                'code': product.default_code,
                'description': product.description,
                'sale_price': product.list_price,
                'image': product.image_512,
                'category': {
                    'id': product.categ_id.id if product.categ_id else None,
                    'name': product.categ_id.name if product.categ_id else None
                }
            } for product in products]

            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }

            return request.make_json_response(
                self._format_response(True, {
                    'products': products_data,
                    'pagination': pagination_data
                }),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving product list"),
                status=500
            )

    @http.route(f"{BASE_URL}/sale", methods=['GET'], auth="public", type="http")
    @paginate_results
    def sale_order(self, page=1, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        Retrieve a paginated list of sales orders with detailed information.

        This endpoint returns all sales orders with their associated order lines,
        customer information, and financial details. Results are ordered by
        most recent order date first.

        Args:
            page (int, optional): Page number to return (1-based index). Defaults to 1.
            limit (int, optional): Number of orders per page. Defaults to DEFAULT_PAGE_SIZE.
            offset (int, optional): Database query offset for pagination. Defaults to 0.

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - data (dict):
                    - orders (list): Sales order objects with:
                        - id (int): Order ID
                        - name (str): Order reference/number
                        - state (str): Current order state (e.g., 'draft', 'confirmed', 'done')
                        - order_date (str|null): Order date in DD-MM-YYYY format
                        - customer (str|null): Customer name
                        - salesman (str|null): Salesperson name
                        - sale_team (str|null): Sales team name
                        - order_lines (list): Order line items with:
                            - product (dict): Product details:
                                - id (int|null): Product ID
                                - name (str|null): Product name
                            - qty (float): Ordered quantity
                            - unit_price (float): Unit price
                            - total (float): Line subtotal (qty * unit_price)
                        - total (dict): Order total amounts including taxes
                    - pagination (dict): Pagination metadata:
                        - total (int): Total number of orders
                        - page (int): Current page number
                        - limit (int): Orders per page
                        - pages (int): Total number of pages

        Notes:
            - Results are ordered by most recent order date first
            - All monetary values are in the company's default currency
            - Order states are mapped to user-friendly values when available
            - Null values indicate missing/undefined relationships

        Raises:
            HTTP 500: If server error occurs during processing

        Example Request:
            GET /api/sale?page=1&limit=10

        Example Success Response:
            {
                "status": true,
                "data": {
                    "orders": [
                        {
                            "id": 1001,
                            "name": "SO1001",
                            "state": "confirmed",
                            "order_date": "15-07-2023",
                            "customer": "Acme Corporation",
                            "salesman": "John Smith",
                            "sale_team": "Direct Sales",
                            "order_lines": [
                                {
                                    "product": {
                                        "id": 45,
                                        "name": "Premium Widget"
                                    },
                                    "qty": 2,
                                    "unit_price": 99.99,
                                    "total": 199.98
                                }
                            ],
                            "total": {
                                "amount_total": 235.98,
                                "amount_tax": 36.00
                            }
                        }
                    ],
                    "pagination": {
                        "total": 25,
                        "page": 1,
                        "limit": 10,
                        "pages": 3
                    }
                }
            }

        Example Error Response:
            {
                "status": false,
                "message": "Error retrieving sales orders",
                "error": "Database connection error"
            }
        """
        try:
            # Get sales orders with pagination
            sale_orders = request.env['sale.order'].sudo().search(
                [],
                limit=limit,
                offset=offset,
                order='date_order desc'
            )

            # Get total count for pagination
            total_count = request.env['sale.order'].sudo().search_count([])

            # Prepare response data
            orders_data = [{
                'id': sale.id,
                'name': sale.name,
                'state': SALE_STATE.get(sale.state, sale.state),
                'order_date': sale.date_order.strftime('%d-%m-%Y') if sale.date_order else None,
                'customer': sale.partner_id.name if sale.partner_id else None,
                'salesman': sale.user_id.name if sale.user_id else None,
                'sale_team': sale.team_id.name if sale.team_id else None,
                'order_lines': [{
                    'product': {
                        'id': line.product_id.id if line.product_id else None,
                        'name': line.product_id.name if line.product_id else None
                    },
                    'qty': line.product_uom_qty,
                    'unit_price': line.price_unit,
                    'total': line.price_subtotal
                } for line in sale.order_line],
                'total': sale.tax_totals
            } for sale in sale_orders]

            pagination_data = {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }

            return request.make_json_response(
                self._format_response(True, {
                    'orders': orders_data,
                    'pagination': pagination_data
                }),
                status=200
            )

        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error retrieving sales orders"),
                status=500
            )

    @http.route(f"{BASE_URL}/order", auth="public", type="http", methods=["POST"], cors="*")
    def new_order(self):
        """
        Create a new sales order with line items and customer information.

        This endpoint validates and processes sales order creation requests, including:
        - Customer validation
        - Order line item validation
        - Price and quantity validation
        - Order creation with all line items

        Request Body:
            JSON object containing:
                - customer_id (int): Required customer ID (must exist)
                - order_line (list[dict]): Required list of order line items with:
                    - product_id (int): Product ID to order
                    - quantity (float): Positive quantity to order
                    - price_unit (float): Non-negative unit price

        Returns:
            dict: JSON response containing:
                - status (bool): Operation success status
                - message (str): Result message
                - data (dict): On success contains:
                    - sale_order_id (int): Created order ID
                    - order_name (str): Generated order reference/number

        Raises:
            HTTP 400: For invalid requests (missing fields, invalid values)
            HTTP 404: If customer not found
            HTTP 500: For server errors during order creation

        Example Request:
            POST /api/order
            {
                "customer_id": 45,
                "order_line": [
                    {
                        "product_id": 101,
                        "quantity": 2,
                        "price_unit": 49.99
                    },
                    {
                        "product_id": 205,
                        "quantity": 1,
                        "price_unit": 129.99
                    }
                ]
            }

        Example Success Response:
            {
                "status": true,
                "message": "Order created successfully",
                "data": {
                    "sale_order_id": 1001,
                    "order_name": "SO1001"
                }
            }

        Example Error Responses:
            {
                "status": false,
                "message": "Invalid customer ID",
                "error": "Customer ID must be positive integer"
            }
            {
                "status": false,
                "message": "Validation failed",
                "error": "Order line must be a non-empty list"
            }
            {
                "status": false,
                "message": "Customer not found",
                "error": "No customer exists with ID 999"
            }
        """
        try:
            # Get request data
            data = self._get_request_data()

            # Handle both direct data and params structure
            if 'params' in data:
                params = data['params']
            else:
                params = data

            # Validate required fields
            customer_id = params.get('customer_id')
            order_line = params.get('order_line', [])

            if not customer_id or customer_id <= 0:
                return request.make_json_response(
                    self._handle_exception(ValueError("Invalid customer ID")),
                    status=400
                )

            if not order_line or not isinstance(order_line, list):
                return request.make_json_response(
                    self._handle_exception(ValueError("Order line must be a non-empty list")),
                    status=400
                )

            # Validate order line items
            for line in order_line:
                if not all(key in line for key in ['product_id', 'quantity', 'price_unit']):
                    return request.make_json_response(
                        self._handle_exception(
                            ValueError("Order line items must contain product_id, quantity, and price_unit")),
                        status=400
                    )

                if line['quantity'] <= 0:
                    return request.make_json_response(
                        self._handle_exception(ValueError("Quantity must be positive")),
                        status=400
                    )

                if line['price_unit'] < 0:
                    return request.make_json_response(
                        self._handle_exception(ValueError("Price must be non-negative")),
                        status=400
                    )

            # Validate customer exists
            customer = request.env['res.partner'].sudo().search([('id', '=', customer_id)], limit=1)
            if not customer:
                return request.make_json_response(
                    self._handle_exception(NotFound("Customer not found")),
                    status=404
                )

            # Create sales order
            sale_order = request.env['sale.order'].sudo().create({
                'partner_id': customer_id,
                'date_order': fields.Datetime.now(),
                'order_line': [
                    (0, 0, {
                        'product_id': line['product_id'],
                        'product_uom_qty': line['quantity'],
                        'price_unit': line['price_unit'],
                    })
                    for line in order_line
                ]
            })

            return request.make_json_response(
                self._format_response(True, {
                    'sale_order_id': sale_order.id,
                    'order_name': sale_order.name
                }, "Order created successfully"),
                status=201
            )

        except json.JSONDecodeError:
            return request.make_json_response(
                self._handle_exception(ValueError("Invalid JSON data")),
                status=400
            )
        except Exception as e:
            return request.make_json_response(
                self._handle_exception(e, "Error creating order"),
                status=500
            )
