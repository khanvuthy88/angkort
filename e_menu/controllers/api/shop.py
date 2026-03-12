from odoo import http
from odoo.http import request
import json
import base64
from .utils import (
    validate_auth, validate_input_data, paginate_results, verify_ownership,
    APIUtilsMixin, PARTNER_FIELDS, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, BASE_URL
)
from .auth import AuthMixin

class ShopAPIController(http.Controller, APIUtilsMixin, AuthMixin):
    
    @http.route(f"{BASE_URL}/shop", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def shop_list(self, **kw):
        """
        Retrieve a paginated list of all shops with search, filter, and sort capabilities.
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
                'banner': self._get_image_url('res.partner', shop.id, 'shop_banner') if shop.shop_banner else '',
                'banks': [self._shop_bank_to_dict(bank) for bank in shop.shop_bank_ids],
                'shop_wifi_ids': [{
                    'id': wifi.id,
                    'name': wifi.name,
                    'password': wifi.password,
                    'wifi_qr_code': self._get_image_url('shop.wifi', wifi.id, 'wifi_qr_code') if wifi.wifi_qr_code else ''
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
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def shop_detail(self, shop_id, **kw):
        """
        Retrieve detailed information for a specific shop.
        """
        try:
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            if not shop:
                return request.make_json_response({'error': 'Shop not found'}, status=404)
            response = {
                'data': {
                    'id': shop.id,
                    'name': shop.name or '',
                    'phoneNumber': self._string_to_string_list(shop.phone) or [],
                    'email': shop.email or '',
                    "address": [shop.customer_address] if shop.customer_address else [],
                    'shop_latitude': shop.shop_latitude or 0.0,
                    'shop_longitude': shop.shop_longitude or 0.0,
                    'banner': self._get_image_url('res.partner', shop.id, 'shop_banner') if shop.shop_banner else '',
                    'shop_wifi_ids': [{
                        'id': wifi.id,
                        'name': wifi.name,
                        'password': wifi.password,
                        'wifi_qr_code': self._get_image_url('shop.wifi', wifi.id, 'wifi_qr_code') if wifi.wifi_qr_code else ''
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
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    def shop_create(self, **kw):
        """
        Create a new shop.
        """
        try:
            data = request.httprequest.form
            files = request.httprequest.files

            # only allow base partner fields from PARTNER_FIELDS
            create_data = {k: v for k, v in data.items() if k in PARTNER_FIELDS}

            # Handle shop related fields using helper method
            shop_related_fields = self._handle_shop_related_fields(data, files, 'create')
            create_data.update(shop_related_fields)

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

                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create shop",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)

            # Create partner (shop). Use create_company context to mark as company/store.
            shop = request.env['res.partner'].sudo().with_context(create_company=True).create([create_data])
            if shop:
                # set the current user's partner parent to the created shop
                try:
                    request.env.user.partner_id.update({'parent_id': shop.id})
                except Exception:
                    pass

            resp = {'id': shop.id, 'name': shop.name}
            return request.make_json_response(resp, status=201)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='shop')
    def shop_update(self, shop_id, **kw):
        """
        Update an existing shop.
        """
        try:
            import json
            import base64

            data = request.httprequest.form
            files = request.httprequest.files

            # only allow base partner fields from PARTNER_FIELDS
            update_fields = {k: v for k, v in data.items() if k in PARTNER_FIELDS}

            # Handle banner file upload (Image field expects base64 string)
            banner_file = files.get('shop_banner')
            if banner_file:
                try:
                    content = banner_file.read()
                    if content:
                        update_fields['shop_banner'] = base64.b64encode(content).decode('utf-8')
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
            wifi_payload = data.get('shop_wifi_ids') or kw.get('shop_wifi_ids')
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
                    update_fields['shop_wifi_ids'] = wifi_commands

            # shop_open_hour_ids: accept JSON array and convert to One2many commands
            hour_payload = data.get('shop_open_hour_ids') or kw.get('shop_open_hour_ids')
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
                    update_fields['shop_open_hour_ids'] = hour_commands

            if not update_fields:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update shop",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)

            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update shop",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }, status=404)

            shop.write(update_fields)
            return request.make_json_response({'message': f'Shop with ID {shop_id} updated successfully'}, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", csrf=False, methods=["PATCH"], cors="*")
    @verify_ownership(entity_type='shop')
    def shop_patch(self, shop_id, **kw):
        """
        Partially update an existing shop.
        """
        try:
            data = request.httprequest.form
            files = request.httprequest.files

            # only allow base partner fields from PARTNER_FIELDS
            update_fields = {k: v for k, v in data.items() if k in PARTNER_FIELDS}

            # Handle shop related fields using helper method
            shop_related_fields = self._handle_shop_related_fields(data, files, 'update')
            update_fields.update(shop_related_fields)

            if not update_fields:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch shop",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)

            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch shop",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }, status=404)

            shop.write(update_fields)
            return request.make_json_response({'message': f'Shop with ID {shop_id} patched successfully'}, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to patch shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='shop')
    def shop_delete(self, shop_id, **kw):
        """
        Delete a shop.
        """
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete shop",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": f"Shop with ID {shop_id} not found"}]
                }, status=404)
            shop.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete shop",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/wifi", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='wifi')
    def shop_wifi_create(self, shop_id, **kw):
        """
        Create a new WiFi entry for a shop.
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
                
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create WiFi",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
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
                'wifi_qr_code': self._get_image_url('shop.wifi', wifi.id, 'wifi_qr_code') if wifi.wifi_qr_code else ''
            }
            
            return request.make_json_response(response_data, status=201)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create WiFi",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/wifi/<int:wifi_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='wifi')
    def shop_wifi_update(self, shop_id, wifi_id, **kw):
        """
        Update a WiFi entry for a shop.
        """
        try:
            data = request.httprequest.form
            wifi_qr_code_file = request.httprequest.files.get('wifi_qr_code')
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Verify WiFi exists and belongs to shop
            wifi = request.env['shop.wifi'].sudo().search([('id', '=', wifi_id), ('shop_id', '=', shop_id)], limit=1)
            if not wifi:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "wifi_id", "message": "WiFi not found"}]
                }, status=404)
            
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
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update WiFi",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)
            
            # Update WiFi entry
            wifi.write(update_data)
            
            response_data = {
                'id': wifi.id,
                'name': wifi.name,
                'password': wifi.password,
                'wifi_qr_code': self._get_image_url('shop.wifi', wifi.id, 'wifi_qr_code') if wifi.wifi_qr_code else ''
            }
            
            return request.make_json_response(response_data, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update WiFi",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/wifi/<int:wifi_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='wifi')
    def shop_wifi_delete(self, shop_id, wifi_id, **kw):
        """
        Delete a WiFi entry from a shop.
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Verify WiFi exists and belongs to shop
            wifi = request.env['shop.wifi'].sudo().search([('id', '=', wifi_id), ('shop_id', '=', shop_id)], limit=1)
            if not wifi:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete WiFi",
                    "statusCode": "404",
                    "errors": [{"name": "wifi_id", "message": "WiFi not found"}]
                }, status=404)
            
            # Delete WiFi entry
            wifi.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete WiFi",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/banner", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='banner')
    def shop_banner_update(self, shop_id, **kw):
        """
        Update shop banner image.
        """
        try:
            banner_file = request.httprequest.files.get('shop_banner')
            
            if not banner_file:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update banner",
                    "statusCode": "400",
                    "errors": [{"name": "shop_banner", "message": "Banner image is required"}]
                }, status=400)
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update banner",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Read and encode banner image
            image_data = banner_file.read()
            encoded_image = base64.b64encode(image_data)
            
            # Update shop banner
            shop.write({'shop_banner': encoded_image})
            
            response_data = {
                'message': 'Banner updated successfully',
                'banner_url': f'/web/image/res.partner/{shop_id}/shop_banner'
            }
            
            return request.make_json_response(response_data, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update banner",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/open-hours", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='open_hour')
    def shop_open_hours_create(self, shop_id, **kw):
        """
        Create a new open hour entry for a shop.
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
                
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)
            
            # Validate day value
            valid_days = ['0', '1', '2', '3', '4', '5', '6']
            if data['day'] not in valid_days:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "400",
                    "errors": [{"name": "day", "message": "Day must be between 0-6 (0=Monday, 6=Sunday)"}]
                }, status=400)
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Check if open hour for this day already exists
            existing_hour = request.env['shop.open.hour'].sudo().search([
                ('shop_id', '=', shop_id),
                ('day', '=', data['day'])
            ], limit=1)
            
            if existing_hour:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create open hour",
                    "statusCode": "400",
                    "errors": [{"name": "day", "message": "Open hour for this day already exists"}]
                }, status=400)
            
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
            
            return request.make_json_response(response_data, status=201)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create open hour",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/open-hours/<int:hour_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='open_hour')
    def shop_open_hours_update(self, shop_id, hour_id, **kw):
        """
        Update an open hour entry for a shop.
        """
        try:
            data = request.httprequest.form
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update open hour",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Verify open hour exists and belongs to shop
            open_hour = request.env['shop.open.hour'].sudo().search([('id', '=', hour_id), ('shop_id', '=', shop_id)], limit=1)
            if not open_hour:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update open hour",
                    "statusCode": "404",
                    "errors": [{"name": "hour_id", "message": "Open hour not found"}]
                }, status=404)
            
            # Validate day value if provided
            if 'day' in data:
                valid_days = ['0', '1', '2', '3', '4', '5', '6']
                if data['day'] not in valid_days:
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to update open hour",
                        "statusCode": "400",
                        "errors": [{"name": "day", "message": "Day must be between 0-6 (0=Monday, 6=Sunday)"}]
                    }, status=400)
                
                # Check if day is being changed and if new day already exists
                if data['day'] != open_hour.day:
                    existing_hour = request.env['shop.open.hour'].sudo().search([
                        ('shop_id', '=', shop_id),
                        ('day', '=', data['day']),
                        ('id', '!=', hour_id)
                    ], limit=1)
                    
                    if existing_hour:
                        return request.make_json_response({
                            "status": "error",
                            "message": "Failed to update open hour",
                            "statusCode": "400",
                            "errors": [{"name": "day", "message": "Open hour for this day already exists"}]
                        }, status=400)
            
            # Prepare update data
            update_data = {}
            if 'day' in data:
                update_data['day'] = data['day']
            if 'open' in data:
                update_data['open'] = data['open']
            if 'close' in data:
                update_data['close'] = data['close']
            
            if not update_data:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update open hour",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)
            
            # Update open hour entry
            open_hour.write(update_data)
            
            response_data = {
                'id': open_hour.id,
                'day': open_hour.day,
                'day_name': dict(open_hour._fields['day'].selection).get(open_hour.day, ''),
                'open': open_hour.open,
                'close': open_hour.close
            }
            
            return request.make_json_response(response_data, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update open hour",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/open-hours/<int:hour_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='open_hour')
    def shop_open_hours_delete(self, shop_id, hour_id, **kw):
        """
        Delete an open hour entry from a shop.
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete open hour",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Verify open hour exists and belongs to shop
            open_hour = request.env['shop.open.hour'].sudo().search([('id', '=', hour_id), ('shop_id', '=', shop_id)], limit=1)
            if not open_hour:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete open hour",
                    "statusCode": "404",
                    "errors": [{"name": "hour_id", "message": "Open hour not found"}]
                }, status=404)
            
            # Delete open hour entry
            open_hour.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete open hour",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/bank", type="http", auth="angkit", csrf=False, methods=["GET"], cors="*")
    @verify_ownership(entity_type='bank')
    def shop_bank_list(self, shop_id, **kw):
        """
        List all bank accounts for a shop.
        """
        try:
            banks = request.env['angkort.shop.bank'].sudo().search(
                [('shop_id', '=', shop_id)],
                order='sequence, id'
            )
            response_data = [self._shop_bank_to_dict(bank) for bank in banks]
            return request.make_json_response(response_data, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to list banks",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/bank/<int:bank_id>", type="http", auth="angkit", csrf=False, methods=["GET"], cors="*")
    @verify_ownership(entity_type='bank')
    def shop_bank_detail(self, shop_id, bank_id, **kw):
        """
        Retrieve a bank account for a shop.
        """
        try:
            bank = request.env['angkort.shop.bank'].sudo().search([
                ('id', '=', bank_id),
                ('shop_id', '=', shop_id)
            ], limit=1)
            if not bank:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to fetch bank",
                    "statusCode": "404",
                    "errors": [{"name": "bank_id", "message": "Bank not found"}]
                }, status=404)
            return request.make_json_response(self._shop_bank_to_dict(bank), status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to fetch bank",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/bank", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='bank')
    def shop_bank_create(self, shop_id, **kw):
        """
        Create a new bank account for a shop.
        """
        try:
            if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                data = request.get_json_data() or {}
            else:
                data = request.httprequest.form
            files = request.httprequest.files

            required_fields = ['name', 'code', 'currency']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                errors = []
                for field in missing_fields:
                    errors.append({"name": field, "message": f"{field.replace('_', ' ').title()} is required"})
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create bank",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)

            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create bank",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)

            currency = data.get('currency')
            if currency not in ('KHR', 'USD'):
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create bank",
                    "statusCode": "400",
                    "errors": [{"name": "currency", "message": "Currency must be KHR or USD"}]
                }, status=400)

            bank_data = {
                'name': data.get('name'),
                'code': data.get('code'),
                'currency': currency,
                'link': data.get('link') or '',
                'shop_id': shop_id,
            }

            if data.get('sequence') is not None:
                try:
                    bank_data['sequence'] = int(data.get('sequence'))
                except (ValueError, TypeError):
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to create bank",
                        "statusCode": "400",
                        "errors": [{"name": "sequence", "message": "Sequence must be a valid integer"}]
                    }, status=400)

            if data.get('active') is not None:
                active_val = str(data.get('active')).lower()
                bank_data['active'] = active_val in ('true', '1', 'yes', 'y')

            logo_file = files.get('logo')
            if logo_file:
                image_data = logo_file.read()
                if image_data:
                    bank_data['logo'] = base64.b64encode(image_data)
            elif data.get('logo'):
                bank_data['logo'] = data.get('logo')

            bank = request.env['angkort.shop.bank'].sudo().create(bank_data)
            return request.make_json_response(self._shop_bank_to_dict(bank), status=201)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create bank",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/bank/<int:bank_id>", type="http", auth="angkit", csrf=False, methods=["PUT"], cors="*")
    @verify_ownership(entity_type='bank')
    def shop_bank_update(self, shop_id, bank_id, **kw):
        """
        Update a bank account for a shop.
        """
        try:
            if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                data = request.get_json_data() or {}
            else:
                data = request.httprequest.form
            files = request.httprequest.files

            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update bank",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)

            bank = request.env['angkort.shop.bank'].sudo().search([('id', '=', bank_id), ('shop_id', '=', shop_id)], limit=1)
            if not bank:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update bank",
                    "statusCode": "404",
                    "errors": [{"name": "bank_id", "message": "Bank not found"}]
                }, status=404)

            update_data = {}
            if data.get('name') is not None:
                update_data['name'] = data.get('name')
            if data.get('code') is not None:
                update_data['code'] = data.get('code')
            if data.get('currency') is not None:
                currency = data.get('currency')
                if currency not in ('KHR', 'USD'):
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to update bank",
                        "statusCode": "400",
                        "errors": [{"name": "currency", "message": "Currency must be KHR or USD"}]
                    }, status=400)
                update_data['currency'] = currency
            if data.get('link') is not None:
                update_data['link'] = data.get('link')

            if data.get('sequence') is not None:
                try:
                    update_data['sequence'] = int(data.get('sequence'))
                except (ValueError, TypeError):
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to update bank",
                        "statusCode": "400",
                        "errors": [{"name": "sequence", "message": "Sequence must be a valid integer"}]
                    }, status=400)

            if data.get('active') is not None:
                active_val = str(data.get('active')).lower()
                update_data['active'] = active_val in ('true', '1', 'yes', 'y')

            logo_file = files.get('logo')
            if logo_file:
                image_data = logo_file.read()
                if image_data:
                    update_data['logo'] = base64.b64encode(image_data)
            elif data.get('logo'):
                update_data['logo'] = data.get('logo')

            if not update_data:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update bank",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)

            bank.write(update_data)
            return request.make_json_response(self._shop_bank_to_dict(bank), status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update bank",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/bank/<int:bank_id>", type="http", auth="angkit", csrf=False, methods=["DELETE"], cors="*")
    @verify_ownership(entity_type='bank')
    def shop_bank_delete(self, shop_id, bank_id, **kw):
        """
        Delete a bank account from a shop.
        """
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete bank",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)

            bank = request.env['angkort.shop.bank'].sudo().search([('id', '=', bank_id), ('shop_id', '=', shop_id)], limit=1)
            if not bank:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete bank",
                    "statusCode": "404",
                    "errors": [{"name": "bank_id", "message": "Bank not found"}]
                }, status=404)

            bank.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete bank",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/create", auth="angkit", type="http", csrf=False, cors="*", methods=["POST"])
    def create_shop(self, **kw):
        """
        Create a new shop (alternative endpoint).
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/category", type="http", auth="angkit", csrf=False, methods=["POST"], cors="*")
    @verify_ownership(entity_type='shop')
    def shop_category_create(self, shop_id, **kw):
        """
        Create a new product category for a shop.
        The category will be automatically attached to the current shop.
        
        Parameters:
        - shop_id (int): ID of the shop to attach the category to
        - name (string): Name of the category (required)
        - parent_id (int): ID of the parent category (optional)
        
        Returns:
        - 201: Category created successfully with category data
        - 400: Validation error (missing required fields)
        - 403: Unauthorized (user doesn't own the shop)
        - 404: Shop not found
        - 500: Server error
        """
        try:
            # Get data from form or JSON
            if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
                data = request.get_json_data()
            else:
                data = request.httprequest.form
            
            # Validate required fields
            if 'name' not in data or not data.get('name'):
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create category",
                    "statusCode": "400",
                    "errors": [{"name": "name", "message": "Category name is required"}]
                }, status=400)
            
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([
                ('id', '=', shop_id),
                ('type', '=', 'store')
            ], limit=1)
            
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create category",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Prepare category data
            category_data = {
                'name': data['name'].strip(),
                'shop_id': shop_id
            }
            
            # Handle parent category if provided
            parent_id = data.get('parent_id')
            if parent_id:
                try:
                    parent_id = int(parent_id)
                    # Verify parent category exists and belongs to the same shop
                    parent_category = request.env['product.category'].sudo().search([
                        ('id', '=', parent_id),
                        ('shop_id', '=', shop_id)
                    ], limit=1)
                    
                    if not parent_category:
                        return request.make_json_response({
                            "status": "error",
                            "message": "Failed to create category",
                            "statusCode": "400",
                            "errors": [{"name": "parent_id", "message": "Parent category not found or doesn't belong to this shop"}]
                        }, status=400)
                    
                    category_data['parent_id'] = parent_id
                except (ValueError, TypeError):
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to create category",
                        "statusCode": "400",
                        "errors": [{"name": "parent_id", "message": "Parent ID must be a valid integer"}]
                    }, status=400)
            
            # Check if category with same name already exists for this shop
            existing_category = request.env['product.category'].sudo().search([
                ('name', '=', category_data['name']),
                ('shop_id', '=', shop_id)
            ], limit=1)
            
            if existing_category:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create category",
                    "statusCode": "400",
                    "errors": [{"name": "name", "message": "A category with this name already exists for this shop"}]
                }, status=400)
            
            # Create the category
            category = request.env['product.category'].sudo().create(category_data)
            
            # Prepare response data
            response_data = {
                'id': category.id,
                'name': category.name,
                'shop_id': category.shop_id.id if category.shop_id else None,
                'shop_name': category.shop_id.name if category.shop_id else None,
                'parent_id': category.parent_id.id if category.parent_id else None,
                'parent_name': category.parent_id.name if category.parent_id else None,
                'complete_name': category.complete_name or category.name,
                'createdAt': category.create_date.isoformat() if category.create_date else None,
                'updatedAt': category.write_date.isoformat() if category.write_date else None
            }
            
            return request.make_json_response({
                "status": "success",
                "message": "Category created successfully",
                "data": response_data
            }, status=201)
            
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create category",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)
