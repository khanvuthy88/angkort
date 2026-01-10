from odoo import http, Command, fields, _
from odoo.http import request, Response
from odoo.exceptions import UserError
from .utils import (
    validate_auth, validate_input_data, paginate_results, 
    APIUtilsMixin, ORDER_STATE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, BASE_URL
)
from .auth import AuthMixin
import logging
import requests

_logger = logging.getLogger(__name__)

class OrderAPIController(http.Controller, APIUtilsMixin, AuthMixin):

    @http.route(f"{BASE_URL}/my/order", auth="angkit", type="http", methods=["GET"], cors="*", csrf=False)
    def my_order(self, **kwargs):
        """
        Retrieve paginated list of orders for the authenticated user with search and ordering capabilities.
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

    @http.route(f"{BASE_URL}/my/order", auth="angkit", type="http", methods=["POST"], cors="*", csrf=False)
    def create_my_order(self):
        """
        Create a new sale order for the authenticated user.
        """
        try:
            # Get authenticated user
            current_user = request.env.user
            if not current_user or current_user.id == request.env.ref('base.public_user').id:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication required',
                    'error': 'User not authenticated'
                }, status=401)

            # Get JSON data
            data = request.get_json_data()
            if not data:
                return request.make_json_response({
                    'status': False,
                    'message': 'No data provided',
                    'error': 'Missing request body'
                }, status=400)
            
            # If the user is passing order_lines inside params
            # data = data.get('params', data) # Standard Odoo JSON-RPC wraps in params, but here we assume raw JSON body for REST

            # Validate order_lines
            if 'order_lines' not in data or not isinstance(data['order_lines'], list):
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing or invalid order_lines',
                    'error': 'order_lines must be a list of order line items'
                }, status=400)

            if not data['order_lines']:
                return request.make_json_response({
                    'status': False,
                    'message': 'Empty order_lines',
                    'error': 'At least one order line is required'
                }, status=400)

            # Create order lines
            order_lines = []
            template_env = request.env['product.template'].sudo()
            variant_env = request.env['product.product'].sudo()
            
            for line in data['order_lines']:
                if not isinstance(line, dict):
                    continue
                    
                if 'product_id' not in line or 'quantity' not in line:
                    return request.make_json_response({
                        'status': False,
                        'message': 'Invalid order line',
                        'error': 'Each order line must contain product_id and quantity'
                    }, status=400)

                product_id = line['product_id']
                quantity = line['quantity']
                
                # Locate product template; accept either template or variant IDs
                product_template = template_env.browse(product_id)
                product_variant = None
                if product_template.exists():
                    product_variant = product_template.product_variant_id
                else:
                    product_variant = variant_env.browse(product_id)
                    if product_variant.exists():
                        product_template = product_variant.product_tmpl_id
                if not product_template or not product_template.exists():
                    return request.make_json_response({
                        'status': False,
                        'message': f'Product not found',
                        'error': f'Product with ID {product_id} does not exist'
                    }, status=400)
                if not product_variant or not product_variant.exists():
                    return request.make_json_response({
                        'status': False,
                        'message': 'Product variant not available',
                        'error': f'No variant found for product ID {product_id}'
                    }, status=400)

                # Validate quantity
                try:
                    quantity = float(quantity)
                    if quantity <= 0:
                        return request.make_json_response({
                            'status': False,
                            'message': 'Invalid quantity',
                            'error': 'Quantity must be greater than 0'
                        }, status=400)
                except (ValueError, TypeError):
                    return request.make_json_response({
                        'status': False,
                        'message': 'Invalid quantity',
                        'error': 'Quantity must be a valid number'
                    }, status=400)

                # Get price_unit (use provided price or product template's list price)
                price_unit = line.get('price_unit')
                if price_unit is None:
                    price_unit = product_template.list_price
                else:
                    try:
                        price_unit = float(price_unit)
                    except (ValueError, TypeError):
                        return request.make_json_response({
                            'status': False,
                            'message': 'Invalid price_unit',
                            'error': 'price_unit must be a valid number'
                        }, status=400)

                order_line = Command.create({
                    'product_id': product_variant.id,
                    'product_uom_qty': quantity,
                    'price_unit': price_unit
                })
                order_lines.append(order_line)

            if not order_lines:
                return request.make_json_response({
                    'status': False,
                    'message': 'No valid order lines',
                    'error': 'At least one valid order line is required'
                }, status=400)

            # Prepare order values
            order_values = {
                'partner_id': current_user.partner_id.id,
                'order_line': order_lines
            }
            
            # Add optional note if provided
            if 'note' in data and data['note']:
                order_values['note'] = data['note']

            # Create sale order
            order = request.env['sale.order'].sudo().create(order_values)

            return request.make_json_response({
                'status': True,
                'message': 'Order created successfully',
                'data': {
                    'order_id': order.id,
                    'order_name': order.name,
                    'partner_id': order.partner_id.id,
                    'partner_name': order.partner_id.name,
                    'date_order': order.date_order.strftime('%Y-%m-%d'),
                    'amount_total': order.amount_total,
                    'state': order.state
                }
            }, status=201)
            
        except Exception as e:
            return request.make_json_response({
                'status': False,
                'message': 'Error creating order',
                'error': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/cart/checkout", auth="angkit", type="json", methods=["POST"], cors="*", csrf=False)
    def cart_checkout(self):
        """
        Validate cart items and check stock availability.
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

    @http.route(f"{BASE_URL}/sale", methods=['GET'], auth="public", type="http", cors="*")
    def global_sale_order(self, **kw):
        """
        Retrieve a paginated list of all sale orders (global, not user-specific) with search, filter, and sort capabilities.
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

    @http.route(f"{BASE_URL}/telegram/order", auth="public", type="http", methods=["POST"], cors="*", csrf=False)
    def telegram_create_order(self):
        """
        Create a new sale order via Telegram Mini App (public endpoint acting as User ID 2).
        
        Expected JSON structure:
        {
            "partner_id": <integer>,  # Required: Customer/partner ID
            "shop_id": <integer>,     # Optional: Store/shop partner ID
            "telegram_id": <integer>, # Optional: Client Telegram ID for notifications
            "order_date": <string>,   # Optional: ISO format date string (e.g., "2025-12-28T10:00:00Z")
            "notes": <string>,        # Optional: Order-level note
            "lines": [                # Required: Array of order line items
                {
                    "template_id": <integer>,           # Required: Product template ID
                    "qty": <float>,                     # Required: Quantity
                    "variant_value_ids": [<int>],       # Optional: Attribute value IDs (Size + Extra Options)
                    "price_unit": <float>,              # Optional: Price override per unit
                    "note": <string>,                   # Optional: Line-level note
                    "addons": [                         # Optional: Separate products (e.g., drinks)
                        {
                            "product_id": <integer>,    # Required: Product variant ID
                            "qty": <float>,             # Required: Quantity
                            "price_unit": <float>,      # Optional: Price override
                            "note": <string>            # Optional: Addon note
                        }
                    ]
                }
            ]
        }
        """
        try:
            # Parse request data
            data = request.get_json_data()
            if not data:
                return request.make_json_response({
                    'status': False,
                    'message': 'No data provided',
                    'error': 'Missing request body'
                }, status=400)

            # Validate required fields
            partner_id = data.get('partner_id')
            lines_data = data.get('lines') or data.get('order_lines')  # Support both for backward compatibility
            
            if not partner_id:
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing required field',
                    'error': 'partner_id is required'
                }, status=400)
            
            if not lines_data or not isinstance(lines_data, list):
                return request.make_json_response({
                    'status': False,
                    'message': 'Missing required field',
                    'error': 'lines (array) is required'
                }, status=400)

            if not lines_data:  # Empty list check
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid lines data',
                    'error': 'lines array cannot be empty'
                }, status=400)

            # Switch to User ID 2 context with sudo
            uid = 2
            sudo_req = request.env(user=uid, su=True)
            
            # Validate and get partner
            try:
                partner_id = int(partner_id)
            except (ValueError, TypeError):
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid partner_id',
                    'error': 'partner_id must be a valid integer'
                }, status=400)
            
            partner = sudo_req['res.partner'].browse(partner_id).exists()
            if not partner:
                return request.make_json_response({
                    'status': False,
                    'message': 'Partner not found',
                    'error': f'Partner with ID {partner_id} does not exist'
                }, status=400)

            # Prepare order header values
            order_vals = {
                'partner_id': partner.id,
                'company_id': partner.company_id.id or sudo_req.company.id,
                'note': data.get('notes') or data.get('note') or '',
            }
            
            # Handle optional order_date (ISO format: "2025-12-28T10:00:00Z" or "2025-12-28T10:00:00")
            order_date = data.get('order_date')
            if order_date:
                try:
                    from datetime import datetime
                    # Parse ISO format date string
                    if isinstance(order_date, str):
                        # Try parsing with ISO format (handles timezone)
                        try:
                            # Replace Z with +00:00 for proper timezone handling
                            date_str = order_date.replace('Z', '+00:00')
                            dt = datetime.fromisoformat(date_str)
                            order_vals['date_order'] = dt
                        except ValueError:
                            # Fallback: try just the date part (YYYY-MM-DD)
                            try:
                                date_only = order_date.split('T')[0]
                                dt = datetime.strptime(date_only, '%Y-%m-%d')
                                order_vals['date_order'] = dt
                            except ValueError:
                                # Invalid date format - skip, use current date
                                pass
                except (ValueError, TypeError):
                    # Invalid date format - skip, use current date
                    pass
            
            # Handle optional shop_id
            shop_id = data.get('shop_id')
            if shop_id:
                try:
                    shop_id = int(shop_id)
                    shop = sudo_req['res.partner'].search([
                        ('id', '=', shop_id), 
                        ('type', '=', 'store')
                    ], limit=1)
                    if shop:
                        order_vals['shop_id'] = shop.id
                except (ValueError, TypeError):
                    pass  # Invalid shop_id - skip silently

            # Create order header
            order = sudo_req['sale.order'].create(order_vals)

            # Prepare model environments
            template_env = sudo_req['product.template']
            variant_env = sudo_req['product.product']
            line_env = sudo_req['sale.order.line']

            # Process each line item
            lines_processed = 0
            for line_idx, line in enumerate(lines_data):
                if not isinstance(line, dict):
                    continue
                    
                # Validate quantity (support both 'qty' and 'quantity')
                quantity = line.get('qty') or line.get('quantity')
                if quantity is None:
                    continue
                
                try:
                    quantity = float(quantity)
                    if quantity <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

                # Identify product (template_id preferred, product_id/variant_id as fallback)
                template_id = line.get('template_id')
                product_id = line.get('product_id') or line.get('variant_id')

                if not (template_id or product_id):
                    continue

                # Resolve main product variant
                resolved_product_id = False
                
                if template_id:
                    try:
                        template_id = int(template_id)
                        template = template_env.browse(template_id).exists()
                        if template:
                            # Get variant value IDs (for Size + Extra Options)
                            variant_value_ids = line.get('variant_value_ids') or []
                            if variant_value_ids:
                                # Convert to list of integers
                                try:
                                    variant_value_ids = [int(vid) for vid in variant_value_ids if vid]
                                    combination = sudo_req['product.template.attribute.value'].browse(variant_value_ids)
                                    variant = template._get_variant_for_combination(combination)
                                    if variant:
                                        resolved_product_id = variant.id
                                except (ValueError, TypeError):
                                    pass
                            
                            # Fallback to default variant if combination doesn't map to a specific variant
                            # (e.g., when using no-variant attributes like Size + Extra Options)
                            if not resolved_product_id:
                                resolved_product_id = template.product_variant_id.id
                    except (ValueError, TypeError):
                        pass
                
                # Fallback: use product_id/variant_id directly
                if not resolved_product_id and product_id:
                    try:
                        product_id = int(product_id)
                        variant = variant_env.browse(product_id).exists()
                        if variant:
                            resolved_product_id = variant.id
                    except (ValueError, TypeError):
                        pass

                if not resolved_product_id:
                    continue

                # Add main item to cart with attributes
                try:
                    variant_value_ids = line.get('variant_value_ids') or []
                    # Ensure variant_value_ids is a list of integers
                    if variant_value_ids:
                        variant_value_ids = [int(vid) for vid in variant_value_ids if vid]
                    else:
                        variant_value_ids = []
                    
                    update_result = order._cart_update(
                        product_id=resolved_product_id,
                        add_qty=quantity,
                        no_variant_attribute_value_ids=variant_value_ids,
                    )
                    
                    if update_result.get('line_id'):
                        sol = line_env.browse(update_result['line_id'])
                        line_updates = {}
                        
                        # Apply price override if provided
                        if line.get('price_unit') is not None:
                            try:
                                line_updates['price_unit'] = float(line['price_unit'])
                            except (ValueError, TypeError):
                                pass
                        
                        # Apply custom note if provided
                        if line.get('note'):
                            note_text = str(line['note']).strip()
                            if note_text:
                                # Append note to existing name or create new
                                existing_name = sol.name or sol.product_id.display_name
                                line_updates['name'] = f"{existing_name}\n{note_text}" if existing_name != note_text else existing_name
                        
                        if line_updates:
                            sol.write(line_updates)
                        
                        lines_processed += 1

                    # Process addons (separate products like drinks)
                    addons = line.get('addons') or []
                    if isinstance(addons, list):
                        for addon in addons:
                            if not isinstance(addon, dict):
                                continue
                            
                            addon_product_id = addon.get('product_id')
                            addon_qty = addon.get('qty') or addon.get('quantity')
                            
                            if not addon_product_id or addon_qty is None:
                                continue
                            
                            try:
                                addon_product_id = int(addon_product_id)
                                addon_qty = float(addon_qty)
                                if addon_qty <= 0:
                                    continue
                                
                                addon_result = order._cart_update(
                                    product_id=addon_product_id,
                                    add_qty=addon_qty,
                                )
                                
                                if addon_result.get('line_id'):
                                    addon_sol = line_env.browse(addon_result['line_id'])
                                    addon_updates = {}
                                    
                                    # Apply price override if provided
                                    if addon.get('price_unit') is not None:
                                        try:
                                            addon_updates['price_unit'] = float(addon['price_unit'])
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    # Apply custom note if provided
                                    if addon.get('note'):
                                        note_text = str(addon['note']).strip()
                                        if note_text:
                                            existing_name = addon_sol.name or addon_sol.product_id.display_name
                                            addon_updates['name'] = f"{existing_name}\n{note_text}" if existing_name != note_text else existing_name
                                    
                                    if addon_updates:
                                        addon_sol.write(addon_updates)
                            except (ValueError, TypeError, UserError):
                                continue  # Skip invalid addons
                                
                except UserError:
                    continue  # Skip problematic lines but continue processing

            # Validate that at least one line was processed
            if lines_processed == 0 or not order.order_line:
                order.unlink()
                return request.make_json_response({
                    'status': False,
                    'message': 'No valid order lines created',
                    'error': 'Ensure product IDs and quantities are valid'
                }, status=400)

            # Send Telegram Notification to Shop Owner
            try:
                if order.shop_id and order.shop_id.telegram_chat_id:
                    self._send_telegram_notification(sudo_req, order, shop_partner=order.shop_id)
                
                # Send Telegram Notification to Client (if provided in request)
                client_telegram_id = data.get('telegram_id') or data.get('telegram_chat_id')
                if client_telegram_id:
                     self._send_telegram_notification(
                        sudo_req, 
                        order, 
                        chat_id=client_telegram_id, 
                        title="✅ Order Confirmation"
                    )

            except Exception as e:
                # Log error but don't fail the request
                _logger.error(f"Failed to send Telegram notification: {str(e)}")

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

    def _send_telegram_notification(self, env, order, shop_partner=None, chat_id=None, title=None):
        """
        Send a Telegram notification to the shop owner or client.
        """
        _logger.info(f"Start sending telegram notification for order: {order.name}")
        try:
            # Get bot token from system parameters
            bot_token = env['ir.config_parameter'].sudo().get_param('telegram.bot.token')
            if not bot_token:
                _logger.warning("Telegram bot token not found")
                return

            if not chat_id and shop_partner:
                chat_id = shop_partner.telegram_chat_id
            
            if not chat_id:
                _logger.warning(f"No telegram chat id found for order {order.name}")
                return

            target_name = shop_partner.name if shop_partner else f"Chat ID {chat_id}"
            _logger.info(f"Sending telegram notification to {target_name}")

            # Format message
            currency_symbol = order.currency_id.symbol or '$'
            total_amount = f"{order.amount_total:.2f} {currency_symbol}"
            
            header = title or "🆕 *New Order Received!*"
            
            message = [
                f"{header}",
                f"🆔 *Order:* {order.name}",
                f"👤 *Customer:* {order.partner_id.name}",
                f"💰 *Total:* {total_amount}",
                f"📝 *Note:* {order.note or 'N/A'}",
                "",
                "*Items:*"
            ]

            for line in order.order_line:
                qty = int(line.product_uom_qty) if line.product_uom_qty.is_integer() else f"{line.product_uom_qty:.2f}"
                line_text = f"• {qty}x {line.name}"
                message.append(line_text)

            message_text = "\n".join(message)

            _logger.info(f"Telegram message log: {message}")

            # Send request to Telegram API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message_text,
                'parse_mode': 'Markdown'
            }
            
            # Use a short timeout to not block the response too long
            response = requests.post(url, json=payload, timeout=5)
            _logger.info(f"Telegram response: {response.status_code} - {response.text}")
            
        except Exception as e:
            _logger.error(f"Failed to send telegram notification: {str(e)}")
            # Re-raise to be caught by caller if needed, or just log
            raise e
