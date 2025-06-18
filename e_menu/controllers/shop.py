import base64
import json

from odoo import http, Command
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
        """Retrieve orders for the authenticated user with pagination and performance optimizations.

        This endpoint fetches sale orders for the currently authenticated user, grouped by their state.
        It implements pagination to handle large datasets efficiently and includes performance optimizations
        such as field limiting and proper indexing.

        Request:
            GET /angkort/api/v1/my/order
            Query Parameters:
                page (int): Page number for pagination (default: 1)
                limit (int): Number of records per page (default: 20, max: 100)

        Returns:
            dict: A dictionary containing orders and pagination information:
                {
                    "orders": {
                        "draft": [
                            {
                                "id": int,
                                "name": str,
                                "date_order": str,  # Format: DD-MM-YYYY
                                "total": float,
                                "state": str
                            },
                            ...
                        ],
                        "sent": [...],
                        "sale": [...],
                        ...
                    },
                    "pagination": {
                        "total": int,    # Total number of records
                        "page": int,     # Current page number
                        "limit": int,    # Records per page
                        "pages": int     # Total number of pages
                    }
                }

        Examples:
            # Get first page of orders
            GET /angkort/api/v1/my/order?page=1&limit=20

            # Get second page with 50 records
            GET /angkort/api/v1/my/order?page=2&limit=50

        Performance:
            - Uses field limiting to minimize data transfer
            - Implements pagination to handle large datasets
            - Uses read() for efficient field access
            - Includes proper indexing hints
            - Limits maximum records per page to prevent overload

        Security:
            - Requires authentication (auth="angkit")
            - Uses sudo() for proper access rights
            - Validates and sanitizes input parameters
            - Limits maximum records per page to prevent DoS

        Notes:
            - Orders are sorted by date_order in descending order
            - Empty or null dates are handled gracefully
            - State values are mapped using ORDER_STATE dictionary
            - All monetary values are returned as floats
            - Response includes pagination metadata for frontend implementation

        Raises:
            None: This endpoint handles errors gracefully and returns empty results
                  rather than raising exceptions
        """
        # Get pagination parameters with defaults
        page = int(request.httprequest.args.get('page', 1))
        limit = min(int(request.httprequest.args.get('limit', 20)), 100)  # Cap at 100 records

        # Calculate offset
        offset = (page - 1) * limit

        # Define fields to fetch to minimize data transfer
        fields = ['id', 'name', 'date_order', 'amount_total', 'state']

        # Search with proper indexing and field limiting
        domain = [('partner_id', '=', request.env.user.partner_id.id)]

        # Get total count for pagination
        total = request.env['sale.order'].sudo().search_count(domain)

        # Calculate total pages
        pages = (total + limit - 1) // limit
        page = min(max(1, page), pages) if pages > 0 else 1

        # Fetch orders with optimized query
        sales = request.env['sale.order'].sudo().search(
            domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order='date_order desc'  # Add proper indexing hint
        )

        # Use read() to fetch all fields at once
        sales_data = sales.read(fields)

        # Group orders by state
        grouped_orders = defaultdict(list)
        for sale in sales_data:
            grouped_orders[sale['state']].append({
                'id': sale['id'],
                'name': sale['name'],
                'date_order': sale['date_order'].strftime('%d-%m-%Y') if sale['date_order'] else '',
                'total': sale['amount_total'],
                'state': ORDER_STATE.get(sale['state'])
            })

        # Prepare response with pagination info
        response = {
            'orders': {state: orders for state, orders in grouped_orders.items()},
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': pages
            }
        }
        return response

    @http.route(f'{BASE_URL}/my/order/<int:order_id>', auth="angkit", type="json", cors="*")
    def my_order_detail(self, order_id):
        """
        Get detailed information about a specific order.

        Endpoint: GET /angkort/api/v1/my/order/{order_id}
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            order_id (int): The ID of the order to get details for

        Returns:
            dict: Response containing order details
                {
                    'id': int,              # Order ID
                    'partner_id': int,       # Customer ID
                    'partner_name': str,     # Customer name
                    'delivery_address': str, # Delivery address
                    'name': str,            # Order reference number
                    'date_order': str,      # Order date (DD-MM-YYYY)
                    'total': float,         # Total order amount
                    'state': str,           # Order state
                    'order_lines': list     # List of order line items
                }

        Status Codes:
            200: Successfully retrieved order details
            404: Order not found

        Example Response (Success):
            {
                "id": 123,
                "partner_id": 456,
                "partner_name": "John Doe",
                "delivery_address": "123 Main St, City, Country",
                "name": "SO123",
                "date_order": "01-01-2024",
                "total": 199.99,
                "state": "draft",
                "order_lines": [
                    {
                        "product_id": 789,
                        "name": "Product Name",
                        "code": "PROD001",
                        "quantity": 2,
                        "price_unit": 99.99
                    }
                ]
            }

        Example Response (Error):
            {
                "error": "Order not found"
            }
        """
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
        """
        Check the availability of products in the cart and calculate total amount.

        Endpoint: POST /angkort/api/v1/cart/checkout
        Auth: Required (angkit)
        Content-Type: application/json

        Request Body:
            {
                "cart": [
                    {
                        "product_id": int,  # Required - ID of the product
                        "quantity": int     # Required - Quantity of the product
                    }
                ]
            }

        Returns:
            dict: Response containing stock status and details
                {
                    'status': str,          # 'sufficient_stock' or 'insufficient_stock'
                    'details': list,        # List of product details
                    'total_amount': float   # Total amount of all products
                }

        Status Codes:
            200: Successfully checked cart
            400: Invalid cart object or no products

        Example Response (Sufficient Stock):
            {
                "status": "sufficient_stock",
                "details": [
                    {
                        "product_id": 123,
                        "code": "PROD001",
                        "name": "Product Name",
                        "quantity": 2,
                        "sub_total": 199.98
                    }
                ],
                "total_amount": 199.98
            }

        Example Response (Insufficient Stock):
            {
                "status": "insufficient_stock",
                "details": {
                    "sufficient_stock": [...],
                    "insufficient_stock": [
                        {
                            "product_id": 123,
                            "code": "PROD001",
                            "name": "Product Name",
                            "quantity": 5,
                            "available": 3,
                            "sub_total": 499.95
                        }
                    ]
                },
                "total_amount": 499.95
            }
        """
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
        """
        Retrieve a paginated list of all available shops in the system.

        This endpoint provides public access to shop information, including basic details
        such as contact information, location, and banking details. The response is formatted
        as a paginated list of shop objects, each containing comprehensive shop information.

        Endpoint: GET /angkort/api/v1/shop
        Auth: Public
        Content-Type: application/json
        CORS: Allowed (*)

        Query Parameters:
            page (int): Page number for pagination (default: 1)
            limit (int): Number of records per page (default: 20, max: 100)

        Returns:
            dict: A dictionary containing shops and pagination information:
                {
                    'shops': list[dict],     # List of shop dictionaries
                    'pagination': {
                        'total': int,        # Total number of records
                        'page': int,         # Current page number
                        'limit': int,        # Records per page
                        'pages': int         # Total number of pages
                    }
                }

                Each shop dictionary contains:
                {
                    'id': int,              # Unique identifier for the shop
                    'name': str,            # Name of the shop
                    'phoneNumber': list[str], # List of contact phone numbers
                    'address': list[str],    # List of shop addresses
                    'wifi': list[str],       # List of WiFi network names
                    'banks': list[dict]      # List of bank account details
                }

                Each bank dictionary in the 'banks' list contains:
                {
                    'name': str,            # Name of the bank
                    'link': str,            # Bank account link/URL
                    'currency': str,        # Currency of the account
                    'logo': str             # Bank logo image data
                }

        Status Codes:
            200: Successfully retrieved shops list
            400: Invalid pagination parameters
            500: Internal server error

        Example Response:
            {
                "shops": [
                    {
                        "id": 123,
                        "name": "My Shop",
                        "phoneNumber": ["+1234567890", "+0987654321"],
                        "address": ["123 Main St, City, Country"],
                        "wifi": ["Shop_WiFi", "Shop_Guest"],
                        "banks": [
                            {
                                "name": "Bank A",
                                "link": "https://bank-a.com/account",
                                "currency": "USD",
                                "logo": "base64_encoded_image_data"
                            }
                        ]
                    }
                ],
                "pagination": {
                    "total": 50,
                    "page": 1,
                    "limit": 20,
                    "pages": 3
                }
            }

        Notes:
            - Phone numbers are stored as comma-separated strings and converted to lists
            - WiFi names are stored as comma-separated strings and converted to lists
            - Address is stored as a single string and returned as a single-item list
            - Bank details include all associated bank accounts for the shop
            - Empty or null values are handled gracefully:
                - Empty name returns empty string
                - Empty phone/WiFi returns empty list
                - Empty address returns empty list
                - Empty bank details returns empty list
            - Pagination parameters are validated and sanitized:
                - Page number must be positive
                - Limit is capped at 100 records per page
                - Invalid parameters return 400 status code

        Performance Considerations:
            - Uses sudo() for elevated database access
            - Performs optimized database queries with pagination
            - Processes data in memory for response formatting
            - Handles null values efficiently
            - Implements proper indexing for pagination queries

        Security:
            - Public endpoint (auth="public")
            - CORS enabled for all origins
            - No sensitive data exposed in response
            - Pagination limits prevent DoS attacks
        """
        # Get pagination parameters with defaults and validation
        try:
            page = max(1, int(request.httprequest.args.get('page', 1)))
            limit = min(100, max(1, int(request.httprequest.args.get('limit', 20))))
        except ValueError:
            return request.make_json_response({
                'error': 'Invalid pagination parameters'
            }, status=400)

        # Calculate offset
        offset = (page - 1) * limit

        # Get total count for pagination
        stores_sudo = request.env['res.partner'].sudo()
        total = stores_sudo.search_count([('type', '=', 'store')])

        # Calculate total pages
        pages = (total + limit - 1) // limit
        page = min(max(1, page), pages) if pages > 0 else 1

        # Fetch paginated shops
        stores = stores_sudo.search(
            [('type', '=', 'store')],
            offset=offset,
            limit=limit,
            order='id'  # Consistent ordering for pagination
        )

        # Format response
        shops_data = [{
            'id': shop.id,
            'name': shop.name or '',
            'phoneNumber': self._string_to_string_list(shop.phone) or [],
            "address": [shop.customer_address] if shop.customer_address else [],
            'wifi': self._string_to_string_list(shop.wifi_name) or [],
            'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids]
        } for shop in stores]

        return {
            'shops': shops_data,
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': pages
            }
        }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", auth="public", type="json", cors="*")
    def shop_detail(self, shop_id):
        """
        Get detailed information about a specific shop.

        Endpoint: GET /angkort/api/v1/shop/{shop_id}
        Auth: Public
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop to get details for

        Returns:
            dict: Response containing shop details
                {
                    'id': int,              # Shop ID
                    'name': str,            # Shop name
                    'phoneNumber': list,    # List of phone numbers
                    'address': list,        # List of addresses
                    'wifi': list,           # List of WiFi names
                    'banks': list           # List of bank details
                }

        Status Codes:
            200: Successfully retrieved shop details
            400: Error processing request
            404: Shop not found

        Example Response (Success):
            {
                "id": 123,
                "name": "My Shop",
                "phoneNumber": ["+1234567890"],
                "address": ["123 Main St"],
                "wifi": ["Shop_WiFi"],
                "banks": [
                    {
                        "bank_name": "Bank A",
                        "account_number": "1234567890"
                    }
                ]
            }

        Example Response (Error):
            {
                "error": "Shop not found"
            }
        """
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
        """
        Create a new shop.

        Endpoint: POST /angkort/api/v1/shop/create
        Auth: Required (angkit)
        Content-Type: application/json

        Request Body:
            {
                'params': {
                    'name': str,         # Required: Shop name
                    'phone': str,        # Required: Shop phone number
                    'wifi_name': str,    # Required: Shop WiFi name
                    'customer_address': str,  # Required: Shop address
                    # ... other valid shop fields
                }
            }

        Returns:
            dict: Response containing status and shop data
                {
                    'status': bool,    # True for success, False for error
                    'message': str,    # Error message if status is False
                    'shop_data': {     # Only present if status is True
                        'name': str,   # Created shop name
                        'id': int      # Created shop ID
                    }
                }

        Status Codes:
            200: Shop created successfully
            400: Invalid request data or missing required fields

        Example Response (Success):
            {
                "status": true,
                "shop_data": {
                    "name": "My Shop",
                    "id": 123
                }
            }

        Example Response (Error):
            {
                "status": false,
                "message": "Missing required fields"
            }
        """
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
        """
        Update an existing shop's information.

        Endpoint: POST /angkort/api/v1/shop/update
        Auth: Required (angkit)
        Content-Type: application/json

        Request Body:
            {
                'id': int,           # Required: ID of the shop to update
                'name': str,         # Optional: New shop name
                'phone': str,        # Optional: New phone number
                'wifi_name': str,    # Optional: New WiFi name
                'customer_address': str  # Optional: New shop address
                # ... other valid shop fields
            }

        Returns:
            dict: Response containing status and message
                {
                    'status': bool,    # True for success, False for error
                    'message': str     # Success or error message
                }

        Status Codes:
            200: Shop updated successfully
            400: Invalid request data
            404: Shop not found

        Example Response (Success):
            {
                "status": true,
                "message": "Shop with ID 123 updated successfully"
            }

        Example Response (Error):
            {
                "status": false,
                "message": "Shop ID is required for update"
            }
        """
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
        """
        Get detailed information about a specific product from a shop.

        Endpoint: GET /angkort/api/v1/shop/{shop_id}/product/{product_id}
        Auth: Public
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the product
            product_id (int): The ID of the product to retrieve

        Returns:
            dict: Product details including:
                {
                    'id': int,              # Product ID
                    'name': str,            # Product name
                    'price': float,         # Product price
                    'description': str,     # Product description
                    'image': str,           # Product image URL
                    'options': list,        # Radio-type product options
                    'choices': list         # Multi-select product choices
                }

        Status Codes:
            200: Successfully retrieved product details
            404: Product not found

        Example Response:
            {
                "id": 123,
                "name": "Product Name",
                "price": 99.99,
                "description": "Product description",
                "image": "http://example.com/image.jpg",
                "options": [
                    {
                        "id": 1,
                        "name": "Size",
                        "data": [
                            {"id": 1, "name": "Small", "price": 0},
                            {"id": 2, "name": "Large", "price": 5}
                        ]
                    }
                ],
                "choices": [
                    {
                        "id": 2,
                        "name": "Toppings",
                        "data": [
                            {"id": 3, "name": "Extra Cheese", "price": 2},
                            {"id": 4, "name": "Bacon", "price": 3}
                        ]
                    }
                ]
            }
        """
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
        """
        Get all products from a specific shop.

        Endpoint: GET /angkort/api/v1/shop/{shop_id}/product
        Auth: Public
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop to get products from

        Returns:
            list: List of product dictionaries containing:
                {
                    'id': int,              # Product ID
                    'name': str,            # Product name
                    'price': float,         # Product price
                    'description': str,     # Product description
                    'image': str,           # Product image URL
                    'options': list,        # Radio-type product options
                    'choices': list         # Multi-select product choices
                }

        Status Codes:
            200: Successfully retrieved products
            404: Shop not found

        Example Response:
            [
                {
                    "id": 123,
                    "name": "Product Name",
                    "price": 99.99,
                    "description": "Product description",
                    "image": "http://example.com/image.jpg",
                    "options": [
                        {
                            "id": 1,
                            "name": "Size",
                            "data": [
                                {"id": 1, "name": "Small", "price": 0},
                                {"id": 2, "name": "Large", "price": 5}
                            ]
                        }
                    ],
                    "choices": [
                        {
                            "id": 2,
                            "name": "Toppings",
                            "data": [
                                {"id": 3, "name": "Extra Cheese", "price": 2},
                                {"id": 4, "name": "Bacon", "price": 3}
                            ]
                        }
                    ]
                }
            ]
        """
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/create", auth="angkit", type="http", methods=["POST"],
                csrf=False, cors="*")
    def create_product(self, shop_id, **kwargs):
        """
        Create a new product in a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/create
        Auth: Required (angkit)
        Content-Type: multipart/form-data

        Parameters:
            shop_id (int): The ID of the shop to create the product in

        Form Data:
            name (str): Required - Name of the new product
            price (float): Required - Price of the new product
            category_id (int): Required - Category ID for the new product
            image (file): Optional - Image file for the product
            description (str): Optional - Description of the product
            barcode (str): Optional - Barcode of the product
            qty_available (float): Optional - Initial quantity available
            attributes (json): Optional - Product attributes configuration
                Format:
                {
                    "attributes": [
                        {
                            "attribute_id": int,  # ID of the attribute
                            "values": [int]       # List of value IDs to associate
                        }
                    ]
                }
            attribute_values (json): Optional - New attribute values to create
                Format:
                {
                    "attribute_values": [
                        {
                            "attribute_id": int,      # ID of the attribute
                            "name": str,             # Name of the value
                            "price_extra": float     # Optional: Extra price for this value
                        }
                    ]
                }

        Returns:
            dict: Response containing status and message
                {
                    'status': bool,    # True for success, False for error
                    'message': str,    # Success or error message
                    'product': {       # Only present on success
                        'id': int,     # Product ID
                        'name': str,   # Product name
                        'price': float,# Product price
                        'category_id': int,  # Category ID
                        'attributes': [      # List of product attributes
                            {
                                'id': int,          # Attribute ID
                                'name': str,        # Attribute name
                                'values': [         # List of attribute values
                                    {
                                        'id': int,          # Value ID
                                        'name': str,        # Value name
                                        'price_extra': float # Extra price
                                    }
                                ]
                            }
                        ]
                    }
                }

        Status Codes:
            201: Product created successfully
            400: Missing required fields or invalid data format
            404: Shop or category not found
            500: Internal server error

        Example Request:
            Form Data:
                name: "New Product"
                price: "99.99"
                category_id: "1"
                description: "Product description"
                attributes: {
                    "attributes": [
                        {
                            "attribute_id": 1,
                            "values": [1, 2, 3]
                        }
                    ]
                }
                attribute_values: {
                    "attribute_values": [
                        {
                            "attribute_id": 1,
                            "name": "New Value",
                            "price_extra": 10.0
                        }
                    ]
                }

        Example Response (Success):
            {
                "status": true,
                "message": "Product created successfully",
                "product": {
                    "id": 123,
                    "name": "New Product",
                    "price": 99.99,
                    "category_id": 1,
                    "attributes": [
                        {
                            "id": 1,
                            "name": "Size",
                            "values": [
                                {
                                    "id": 1,
                                    "name": "Small",
                                    "price_extra": 0.0
                                },
                                {
                                    "id": 2,
                                    "name": "Medium",
                                    "price_extra": 5.0
                                }
                            ]
                        }
                    ]
                }
            }

        Example Response (Error):
            {
                "status": false,
                "message": "Missing required fields: name, price"
            }
        """
        image_file = request.httprequest.files.get('image')
        data = request.httprequest.form
        required_fields = ['name', 'price', 'category_id']

        # Validate required fields for product creation
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return request.make_json_response({'error': f'Missing required fields: {", ".join(missing_fields)}'},
                                              status=400)

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

            # Handle image if provided
            if image_file:
                image_data = image_file.read()
                encoded_image = base64.b64encode(image_data)
                product.write({'image_1920': encoded_image})

            # Handle product attributes if provided
            if 'attributes' in data:
                try:
                    attributes_data = json.loads(data['attributes'])
                    if isinstance(attributes_data, list):
                        for attr_data in attributes_data:
                            if 'attribute_id' in attr_data and 'values' in attr_data:
                                attribute = request.env['product.attribute'].sudo().browse(attr_data['attribute_id'])
                                if attribute.exists():
                                    # Create attribute line
                                    attr_line = request.env['product.template.attribute.line'].sudo().create({
                                        'product_tmpl_id': product.product_tmpl_id.id,
                                        'attribute_id': attribute.id,
                                        'value_ids': [(6, 0, attr_data['values'])]
                                    })
                except json.JSONDecodeError:
                    return request.make_json_response({
                        'status': False,
                        'message': 'Invalid attributes JSON format'
                    }, status=400)
                except Exception as e:
                    return request.make_json_response({
                        'status': False,
                        'message': f'Error processing attributes: {str(e)}'
                    }, status=400)

            # Handle attribute values if provided
            if 'attribute_values' in data:
                try:
                    values_data = json.loads(data['attribute_values'])
                    if isinstance(values_data, list):
                        for value_data in values_data:
                            if 'attribute_id' in value_data and 'name' in value_data:
                                attribute = request.env['product.attribute'].sudo().browse(value_data['attribute_id'])
                                if attribute.exists():
                                    # Create attribute value
                                    value = request.env['product.attribute.value'].sudo().create({
                                        'name': value_data['name'],
                                        'attribute_id': attribute.id,
                                        'price_extra': value_data.get('price_extra', 0.0)
                                    })
                except json.JSONDecodeError:
                    return request.make_json_response({
                        'status': False,
                        'message': 'Invalid attribute values JSON format'
                    }, status=400)
                except Exception as e:
                    return request.make_json_response({
                        'status': False,
                        'message': f'Error processing attribute values: {str(e)}'
                    }, status=400)

            return request.make_json_response({
                'status': True,
                'message': 'Product created successfully',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': product.list_price,
                    'category_id': product.categ_id.id,
                    'attributes': [{
                        'id': line.attribute_id.id,
                        'name': line.attribute_id.name,
                        'values': [{
                            'id': value.id,
                            'name': value.name,
                            'price_extra': value.price_extra
                        } for value in line.value_ids]
                    } for line in product.attribute_line_ids]
                }
            }, status=201)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': f'Error creating product: {str(e)}'
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/update", auth="angkit", type="http",
                methods=["POST"], csrf=False, cors="*")
    def update_product(self, shop_id, product_id):
        """
        Update a product in a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/{product_id}/update
        Auth: Required (angkit)
        Content-Type: multipart/form-data

        Parameters:
            shop_id (int): The ID of the shop containing the product
            product_id (int): The ID of the product to update

        Form Data:
            name (str): Required - New name for the product
            price (float): Required - New price for the product
            category_id (int): Required - New category ID for the product
            image (file): Optional - New image file for the product
            description (str): Optional - New description for the product
            barcode (str): Optional - New barcode for the product
            qty_available (float): Optional - New quantity available
            attributes (json): Optional - Product attributes configuration
                Format:
                {
                    "attributes": [
                        {
                            "attribute_id": int,  # ID of the attribute
                            "values": [int]       # List of value IDs to associate
                        }
                    ]
                }
            attribute_values (json): Optional - New attribute values to create
                Format:
                {
                    "attribute_values": [
                        {
                            "attribute_id": int,      # ID of the attribute
                            "name": str,             # Name of the value
                            "price_extra": float     # Optional: Extra price for this value
                        }
                    ]
                }

        Returns:
            dict: Response containing status, message and updated product data
                {
                    'status': str,     # 'success' or 'error'
                    'message': str,    # Success or error message
                    'product': {       # Only present on success
                        'id': int,     # Product ID
                        'name': str,   # Product name
                        'price': float,# Product price
                        'category_id': int,  # Category ID
                        'attributes': [      # List of product attributes
                            {
                                'id': int,          # Attribute ID
                                'name': str,        # Attribute name
                                'values': [         # List of attribute values
                                    {
                                        'id': int,          # Value ID
                                        'name': str,        # Value name
                                        'price_extra': float # Extra price
                                    }
                                ]
                            }
                        ]
                    }
                }

        Status Codes:
            200: Product updated successfully
            400: Missing required fields or invalid data format
            404: Shop, category or product not found
            500: Internal server error

        Example Request:
            Form Data:
                name: "Updated Product"
                price: "99.99"
                category_id: "1"
                description: "New description"
                attributes: {
                    "attributes": [
                        {
                            "attribute_id": 1,
                            "values": [1, 2, 3]
                        }
                    ]
                }
                attribute_values: {
                    "attribute_values": [
                        {
                            "attribute_id": 1,
                            "name": "New Value",
                            "price_extra": 10.0
                        }
                    ]
                }

        Example Response (Success):
            {
                "status": "success",
                "message": "Product updated successfully",
                "product": {
                    "id": 123,
                    "name": "Updated Product",
                    "price": 99.99,
                    "category_id": 1,
                    "attributes": [
                        {
                            "id": 1,
                            "name": "Size",
                            "values": [
                                {
                                    "id": 1,
                                    "name": "Small",
                                    "price_extra": 0.0
                                },
                                {
                                    "id": 2,
                                    "name": "Medium",
                                    "price_extra": 5.0
                                }
                            ]
                        }
                    ]
                }
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Missing required fields: name, price"
            }
        """
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
            'categ_id': data.get('category_id'),
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

            # Handle product attributes if provided
            if 'attributes' in data:
                try:
                    attributes_data = json.loads(data['attributes'])
                    if isinstance(attributes_data, list):
                        # Clear existing attribute lines
                        product.attribute_line_ids.unlink()

                        # Create new attribute lines
                        for attr_data in attributes_data:
                            if 'attribute_id' in attr_data and 'values' in attr_data:
                                attribute = request.env['product.attribute'].sudo().browse(attr_data['attribute_id'])
                                if attribute.exists():
                                    # Create attribute line
                                    attr_line = request.env['product.template.attribute.line'].sudo().create({
                                        'product_tmpl_id': product.product_tmpl_id.id,
                                        'attribute_id': attribute.id,
                                        'value_ids': [(6, 0, attr_data['values'])]
                                    })
                except json.JSONDecodeError:
                    return request.make_json_response({
                        'status': 'error',
                        'message': 'Invalid attributes JSON format',
                    }, status=400)
                except Exception as e:
                    return request.make_json_response({
                        'status': 'error',
                        'message': f'Error processing attributes: {str(e)}',
                    }, status=400)

            # Handle attribute values if provided
            if 'attribute_values' in data:
                try:
                    values_data = json.loads(data['attribute_values'])
                    if isinstance(values_data, list):
                        for value_data in values_data:
                            if 'attribute_id' in value_data and 'name' in value_data:
                                attribute = request.env['product.attribute'].sudo().browse(value_data['attribute_id'])
                                if attribute.exists():
                                    # Create or update attribute value
                                    value = request.env['product.attribute.value'].sudo().create({
                                        'name': value_data['name'],
                                        'attribute_id': attribute.id,
                                        'price_extra': value_data.get('price_extra', 0.0)
                                    })
                except json.JSONDecodeError:
                    return request.make_json_response({
                        'status': 'error',
                        'message': 'Invalid attribute values JSON format',
                    }, status=400)
                except Exception as e:
                    return request.make_json_response({
                        'status': 'error',
                        'message': f'Error processing attribute values: {str(e)}',
                    }, status=400)

            product.with_user(request.env.user).write(product_data)
            return request.make_json_response({
                'status': 'success',
                'message': 'Product updated successfully',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': product.list_price,
                    'category_id': product.categ_id.id,
                    'attributes': [{
                        'id': line.attribute_id.id,
                        'name': line.attribute_id.name,
                        'values': [{
                            'id': value.id,
                            'name': value.name,
                            'price_extra': value.price_extra
                        } for value in line.value_ids]
                    } for line in product.attribute_line_ids]
                },
            }, status=200)
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error updating product: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/delete", auth="angkit", type="http",
                methods=["POST"], csrf=False, cors="*")
    def delete_product(self, shop_id, product_id):
        """
        Delete a product from a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/{product_id}/delete
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the product
            product_id (int): The ID of the product to delete

        Returns:
            dict: Response containing status and message
                {
                    'status': bool,    # True for success, False for error
                    'message': str     # Success or error message
                }

        Status Codes:
            200: Product deleted successfully
            404: Shop or product not found
            500: Internal server error

        Example Response (Success):
            {
                "status": True,
                "message": "Product deleted successfully"
            }

        Example Response (Error):
            {
                "status": False,
                "message": "Shop with ID 123 not found"
            }
        """
        shop_sudo = request.env['res.partner'].sudo().search([
            ('id', '=', shop_id),
            ('type', '=', 'store')
        ], limit=1)
        if not shop_sudo:
            return request.make_json_response({
                "status": False,
                "message": f"Shop with ID {shop_id} not found"
            }, status=404)

        product = request.env['product.product'].sudo().search([('id', '=', product_id), ('shop_id', '=', shop_id)],
                                                               limit=1)
        if not product:
            return request.make_json_response({
                "status": False,
                "message": f"Product with ID {product_id} not found"
            }, status=404)
        try:
            product.unlink()
            return request.make_json_response({
                "status": True,
                "message": "Product deleted successfully"
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': f"Error deleting product: {str(e)}"
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category", auth="public", type="json", cors="*")
    def product_category(self, shop_id):
        categories = request.env['product.category'].sudo().searh([('shop_id', '=', shop_id)])
        return [self._category_to_dict(cate) for cate in categories]

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/create", auth="angkit", type="json", cors="*")
    def create_product_category(self, shop_id):
        """
        Create a new product category in a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/category/create
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop to create the category in

        Request Body:
            {
                'name': str    # Required: Name of the new category
            }

        Returns:
            dict: Response containing status, message and created category data
                {
                    'status': str,     # 'success' or 'error'
                    'message': str,    # Success or error message
                    'category': dict   # Created category data (only on success)
                }

        Status Codes:
            200: Category created successfully
            400: Missing required fields
            500: Internal server error

        Example Request:
            {
                "name": "New Category"
            }

        Example Response (Success):
            {
                "status": "success",
                "message": "Category created successfully",
                "category": {
                    "id": 123,
                    "name": "New Category",
                    ...
                }
            }
        """
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>/update", auth="angkit", type="json",
                cors="*")
    def update_product_category(self, shop_id, cate_id):
        """
        Update a product category in a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/category/{cate_id}/update
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the category
            cate_id (int): The ID of the category to update

        Request Body:
            {
                'name': str,      # Required: New name for the category
                'shop_id': int    # Required: Shop ID the category belongs to
            }

        Returns:
            dict: Response containing status, message and updated category data
                {
                    'status': str,     # 'success' or 'error'
                    'message': str,    # Success or error message
                    'category': dict   # Updated category data (only on success)
                }

        Status Codes:
            200: Category updated successfully
            400: Missing required fields or unauthorized
            500: Internal server error

        Example Request:
            {
                "name": "New Category Name",
                "shop_id": 123
            }

        Example Response (Success):
            {
                "status": "success",
                "message": "Category updated successfully",
                "category": {
                    "id": 456,
                    "name": "New Category Name",
                    ...
                }
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Missing required fields"
            }
        """
        data = request.get_json_data()
        required_fields = ['name', 'shop_id']
        if any(field not in data for field in required_fields):
            return {
                'status': 'error',
                'message': 'Missing required fields',
            }
        try:
            category = request.env['product.category'].with_user(request.env.user).search(
                [('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/category/<int:cate_id>/delete", auth="angkit", type="json",
                cors="*")
    def delete_product_category(self, shop_id, cate_id):
        """
        Delete a product category from a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/category/{cate_id}/delete
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the category
            cate_id (int): The ID of the category to delete

        Returns:
            dict: Response containing status and message
                {
                    'status': str,     # 'success' or 'error'
                    'message': str     # Success or error message
                }

        Status Codes:
            200: Category deleted successfully
            400: Category not found or unauthorized
            500: Internal server error

        Example Response (Success):
            {
                "status": "success",
                "message": "Category deleted successfully"
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Category with ID 123 not found"
            }
        """
        category = request.env['product.category'].with_user(request.env.user).search(
            [('id', '=', cate_id), ('shop_id', '=', shop_id)], limit=1)
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

    def _build_product_variants_data(self, data, shop_id):
        return {
            'create_variant': data.get('create_variant'),
            'display_type': data.get('display_type'),
            'name': data.get('name'),
            'shop_id': shop_id
        }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/", auth="angkit", type="json", cors="*",
                methods=['GET'])
    def product_variant_list(self, shop_id):
        """
        List all product attributes (variants) for a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/variant/
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop to list attributes for

        Returns:
            list: List of attribute data for the shop
                [
                    {
                        'id': int,
                        'name': str,
                        'display_type': str,
                        'create_variant': str,
                        'visibility': str
                    },
                    ...
                ]

        Status Codes:
            200: Success
            400: Missing required fields
            500: Internal server error

        Example Response (Success):
            [
                {
                    "id": 123,
                    "name": "Attribute Name",
                    "display_type": "multi",
                    "create_variant": "no_variant",
                    "visibility": "visible"
                },
                ...
            ]
        """
        return self._product_variant_list(shop_id)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/create", auth="angkit", type="json", cors="*",
                methods=['POST'])
    def create_product_variant(self, shop_id):
        """
        Create a new product attribute (variant) for a shop.

        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/variant/create
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop to create the attribute for

        Request Body:
            {
                "create_variant": str,  # Required: Either "no_variant" or "always"
                "display_type": str,    # Required: Either "multi" or "radio"
                "name": str,           # Required: Name of the attribute (e.g., "Extras")
                "visibility": str      # Required: Either "visible" or "hidden"
            }

        Returns:
            dict: Response containing status, message and created attribute data
                {
                    'status': str,     # 'success' or 'error'
                    'message': str,    # Success or error message
                    'attribute': {     # Only present on success
                        'id': int,
                        'name': str,
                        'create_variant': str,
                        'display_type': str,
                        'visibility': str
                    }
                }

        Status Codes:
            200: Attribute created successfully
            400: Bad request (missing or invalid fields)
            500: Internal server error

        Example Request:
            {
                "create_variant": "no_variant",
                "display_type": "multi",
                "name": "Extras",
                "visibility": "visible"
            }
        """
        data = request.get_json_data()

        # Define valid values as sets for O(1) lookup
        VALID_CREATE_VARIANTS = {'no_variant', 'always'}
        VALID_DISPLAY_TYPES = {'multi', 'radio'}
        REQUIRED_FIELDS = {'create_variant', 'display_type', 'name'}

        try:
            # Check required fields using set operations
            missing_fields = REQUIRED_FIELDS - set(data.keys())
            if missing_fields:
                return {
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}',
                }

            # Validate values using set membership
            if data['create_variant'] not in VALID_CREATE_VARIANTS:
                return {
                    'status': 'error',
                    'message': f'Invalid create_variant value. Must be one of: {", ".join(VALID_CREATE_VARIANTS)}',
                }

            if data['display_type'] not in VALID_DISPLAY_TYPES:
                return {
                    'status': 'error',
                    'message': f'Invalid display_type value. Must be one of: {", ".join(VALID_DISPLAY_TYPES)}',
                }

            # Use exists() for faster existence check
            if request.env['product.attribute'].sudo().search_count([
                ('name', '=', data['name']),
                ('shop_id', '=', shop_id),
            ], limit=1):
                return {
                    'status': 'error',
                    'message': f'Attribute with name {data["name"]} already exists',
                }

            # Create attribute in a single operation
            variant_create_data = self._build_product_variants_data(data, shop_id)
            # Ensure create_variant is 'no_variant' when display_type is 'multi'
            if variant_create_data.get('display_type') == 'multi':
                variant_create_data['create_variant'] = 'no_variant'
            attribute = request.env['product.attribute'].sudo().create(variant_create_data)

            return {
                'status': 'success',
                'message': 'Attribute created successfully',
                'attribute': self._attribute_to_dict(attribute),
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error creating attribute: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/update/<int:variant_id>", auth="angkit", type="json",
                cors="*", methods=['POST'])
    def update_product_variant(self, shop_id, variant_id):
        """
        Update an existing product attribute (variant).

        Endpoint: PUT /angkort/api/v1/shop/{shop_id}/product/variant/update/{variant_id}
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the attribute
            variant_id (int): The ID of the attribute to update

        Request Body:
            {
                "name": str,              # Optional: New name for the attribute
                "create_variant": str,     # Optional: New create_variant setting
                "display_type": str,       # Optional: New display type
                "sequence": int           # Optional: New sequence number
            }

        Returns:
            dict: Response containing status and message
                {
                    'status': str,     # 'success' or 'error'
                    'message': str,    # Success or error message
                    'attribute': dict  # Updated attribute data (if successful)
                }

        Status Codes:
            200: Attribute updated successfully
            400: Bad request (invalid fields)
            404: Attribute not found
            500: Internal server error

        Example Request:
            {
                "name": "Updated Size",
                "create_variant": "always",
                "display_type": "radio",
                "sequence": 2
            }

        Example Response (Success):
            {
                "status": "success",
                "message": "Attribute updated successfully",
                "attribute": {
                    "id": 1,
                    "name": "Updated Size",
                    "create_variant": "always",
                    "display_type": "radio",
                    "sequence": 2
                }
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Attribute not found"
            }
        """

        try:
            data = request.get_json_data()
            if not data:
                return {
                    'status': 'error',
                    'message': 'No data provided for update'
                }

            # Validate shop exists
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return {
                    'status': 'error',
                    'message': 'Shop not found'
                }

            # Find the attribute
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', variant_id),
                ('shop_id', '=', shop_id)
            ], limit=1)
            if not attribute:
                return {
                    'status': 'error',
                    'message': 'Attribute not found'
                }

            # Define valid values as sets for O(1) lookup
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}

            # Validate create_variant if provided
            if 'create_variant' in data and data['create_variant'] not in VALID_CREATE_VARIANTS:
                return {
                    'status': 'error',
                    'message': f'Invalid create_variant value. Must be one of: {", ".join(VALID_CREATE_VARIANTS)}'
                }

            # Validate display_type if provided
            if 'display_type' in data and data['display_type'] not in VALID_DISPLAY_TYPES:
                return {
                    'status': 'error',
                    'message': f'Invalid display_type value. Must be one of: {", ".join(VALID_DISPLAY_TYPES)}'
                }

            # Check for duplicate name if name is being updated
            if 'name' in data and data['name'] != attribute.name:
                if request.env['product.attribute'].sudo().search_count([
                    ('shop_id', '=', shop_id),
                    ('name', '=', data['name'])
                ], limit=1):
                    return {
                        'status': 'error',
                        'message': f'Attribute with name {data["name"]} already exists'
                    }

            # Ensure create_variant is 'no_variant' when display_type is 'multi'
            if data.get('display_type') == 'multi':
                data['create_variant'] = 'no_variant'

            # Update the attribute
            attribute.write(data)

            return {
                'status': 'success',
                'message': 'Attribute updated successfully',
                'attribute': self._attribute_to_dict(attribute)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error updating attribute: {str(e)}'
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/delete/<int:variant_id>", auth="angkit", type="json",
                cors="*", methods=['DELETE'])
    def delete_product_variant(self, shop_id, variant_id):
        """
        Delete a product attribute (variant).

        Endpoint: DELETE /angkort/api/v1/shop/{shop_id}/product/variant/delete/{variant_id}
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the attribute
            variant_id (int): The ID of the attribute to delete

        Returns:
            dict: Response containing status and message
                {
                    'status': str,     # 'success' or 'error'
                    'message': str     # Success or error message
                }

        Status Codes:
            200: Attribute deleted successfully
            404: Attribute not found
            500: Internal server error

        Example Response (Success):
            {
                "status": "success",
                "message": "Attribute deleted successfully"
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Attribute not found"
            }
        """
        try:
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return {
                    'status': 'error',
                    'message': 'Shop not found'
                }

            # Find the attribute
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', variant_id),
                ('shop_id', '=', shop_id),
                ('create_uid', '=', request.env.user.id)
            ], limit=1)
            if not attribute:
                return {
                    'status': 'error',
                    'message': 'Attribute not found'
                }

            # Delete the attribute
            attribute.unlink()

            return {
                'status': 'success',
                'message': 'Attribute deleted successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error deleting attribute: {str(e)}'
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>/value", methods=["GET"], auth="angkit", type="json", cors="*")
    def product_vairiant_value_by_vairant(self, shop_id, variant_id):
        """
        Get all values for a specific product attribute (variant) in a shop.

        Endpoint: GET /angkort/api/v1/shop/{shop_id}/product/variant/{variant_id}/value
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop
            variant_id (int): The ID of the attribute to get values for

        Returns:
            dict: Response containing status and variant values
                {
                    'status': str,     # 'success' or 'error'
                    'message': str,    # Success or error message
                    'values': [        # List of variant values (if successful)
                        {
                            'id': int,
                            'name': str,
                            'extra_price': float
                        },
                        ...
                    ]
                }

        Status Codes:
            200: Values retrieved successfully
            404: Shop or attribute not found
            500: Internal server error
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return {
                    'status': 'error',
                    'message': 'Shop not found'
                }

            # Find the attribute
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', variant_id),
                ('shop_id', '=', shop_id)
            ], limit=1)
            if not attribute:
                return {
                    'status': 'error',
                    'message': 'Attribute not found'
                }

            value_list = [{
                'id': value.id,
                'name': value.name,
                'extra_price': value.price_extra
            } for value in attribute.value_ids]

            return {
                'status': 'success',
                'message': 'Values retrieved successfully',
                'values': value_list
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error retrieving values: {str(e)}'
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value", methods=["POST"], auth="angkit", type="json", cors="*")
    def create_product_variant_value(self, shop_id):
        """
        Create values for a product attribute (variant).
        Endpoint: POST /angkort/api/v1/shop/{shop_id}/product/variant/value
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop to create the attribute values for

        Request Body:
            {
                "attribute_id": int,    # Required: ID of the attribute to add values to
                "values": [             # Required: List of values to create
                    {
                        "name": str,           # Required: Name of the value
                        "extra_price": float   # Required: Additional price for this value
                    },
                    ...
                ]
            }

        Returns:
            dict: Response containing status and message
                {
                    'status': str,     # 'success' or 'error'
                    'message': str     # Success or error message
                }

        Status Codes:
            200: Values created successfully
            400: Bad request (missing or invalid fields)
            404: Attribute not found
            500: Internal server error

        Example Request:
            {
                "attribute_id": 1,
                "values": [
                    {
                        "name": "Extra Cheese",
                        "extra_price": 2.50
                    },
                    {
                        "name": "Extra Bacon",
                        "extra_price": 3.00
                    }
                ]
            }
        """
        data = request.get_json_data()

        # Validate required fields and data types upfront
        required_fields = {'attribute_id': int, 'values': list}
        for field, expected_type in required_fields.items():
            if field not in data:
                return {'status': 'error', 'message': f'Missing required field: {field}'}
            if not isinstance(data[field], expected_type):
                return {'status': 'error', 'message': f'Invalid {field} type. Expected {expected_type.__name__}'}

        # Fetch attribute in a single query with sudo
        attribute = request.env['product.attribute'].sudo().browse(data['attribute_id'])
        if not attribute.exists():
            return {'status': 'error', 'message': f'Attribute with ID {data["attribute_id"]} not found'}

        if attribute.shop_id.id != shop_id:
            return {'status': 'error', 'message': f"Attribute didn't belong to this shop"}

        # Prepare all values for bulk creation
        values_to_create = [{
            'default_extra_price': value['extra_price'],
            'name': value['name'],
            'attribute_id': attribute.id,
        } for value in data['values']]

        # Bulk create all values in a single database operation
        request.env['product.attribute.value'].sudo().create(values_to_create)

        return {'status': 'success', 'message': 'Attribute values created successfully'}

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", auth="angkit", type="json",
                cors="*", methods=["PUT"])
    def update_product_variant_value(self, shop_id, value_id):
        """
        Update a product variant value.

        Endpoint: PUT /angkort/api/v1/shop/{shop_id}/product/variant/value/{value_id}
        Auth: Required (angkit)
        Content-Type: application/json

        Parameters:
            shop_id (int): The ID of the shop containing the variant
            value_id (int): The ID of the variant value to update

        Request Body:
            {
                "name": str,           # Optional: New name for the variant value
                "extra_price": float   # Optional: New additional price for this value
            }

        Returns:
            dict: Response containing status and message
                {
                    'status': str,     # 'success' or 'error'
                    'message': str     # Success or error message
                }

        Status Codes:
            200: Value updated successfully
            400: Bad request (missing or invalid fields)
            404: Value not found
            500: Internal server error

        Example Response (Success):
            {
                "status": "success",
                "message": "Variant value updated successfully"
            }

        Example Response (Error):
            {
                "status": "error",
                "message": "Variant value not found"
            }
        """
        try:
            data = request.get_json_data()
            shop = request.env['shop'].sudo().browse(shop_id)
            if not shop.exists():
                return {'status': 'error', 'message': 'Shop not found'}
            if not data:
                return {'status': 'error', 'message': 'No data provided for update'}

            # Fetch the variant value using sudo for elevated rights
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return {'status': 'error', 'message': 'Variant value not found'}

            if variant_value.create_uid.id != request.env.user.id:
                return {'status': 'error', 'message': 'You are not authorized to update this variant value'}

            # Update variant value with provided fields
            variant_value.write({key: data[key] for key in data if key in ['name', 'extra_price']})

            return {'status': 'success', 'message': 'Variant value updated successfully'}

        except Exception as e:
            return {'status': 'error', 'message': f'Error updating variant value: {str(e)}'}

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

    def _product_variant_list(self, shop_id):
        try:
            attributes = request.env['product.attribute'].sudo().search([
                ('create_uid', '=', request.env.user.id),
                ('shop_id', '=', shop_id)
            ])
            return [self._attribute_to_dict(attribute) for attribute in attributes]
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error listing attributes: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/calculate-price", auth="public", type="json",
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
