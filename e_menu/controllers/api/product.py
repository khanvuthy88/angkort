from odoo import http
from odoo.http import request
import json
import base64
from .utils import (
    validate_auth, validate_input_data, paginate_results, verify_ownership,
    APIUtilsMixin, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, BASE_URL
)
from .auth import AuthMixin

class ProductAPIController(http.Controller, APIUtilsMixin, AuthMixin):

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
                'message': f'Error converting  te to dictionary: {str(e)}',
            }

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def product_list(self, shop_id, **kw):
        """
        Retrieve all products for a given shop with search, filter, and sort capabilities.
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({'error': 'Shop not found'}, status=404)
            
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
                    domain.append(('list_price', '>=', price_min))  # type: ignore
                except ValueError:
                    pass
            
            if filter_price_max:
                try:
                    price_max = float(filter_price_max)
                    domain.append(('list_price', '<=', price_max))  # type: ignore
                except ValueError:
                    pass
            
            if filter_has_variants:
                if filter_has_variants.lower() == 'true':
                    domain.append(('attribute_line_ids', '!=', False))
                elif filter_has_variants.lower() == 'false':
                    domain.append(('attribute_line_ids', '=', False))
            
            # Calculate pagination
            offset = (page - 1) * limit
            total = request.env['product.template'].sudo().search_count(domain)
            page_count = (total + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch products
            products = request.env['product.template'].sudo().search(
                domain,
                offset=offset,
                limit=limit,
                order=order_clause
            )
            
            products_data = []
            for product in products:
                product_data = self._product_to_dict(product)
                product_data['options'] = [self._get_product_options(option) for option in product.attribute_line_ids.filtered(
                    lambda x: x.attribute_id.display_type == 'radio')]
                product_data['choices'] = [self._get_product_choices(choice) for choice in product.attribute_line_ids.filtered(
                    lambda x: x.attribute_id.display_type == 'multi')]
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
            
            response = {
                'data': products_data,
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
            return request.make_json_response({
                'error': 'Error retrieving products',
                'message': str(e)
            }, status=500)

    @http.route(f"{BASE_URL}/product/mine", type="http", auth="angkit", methods=["GET"], cors="*", csrf=False)
    def product_mine(self, **kw):
        """
        Retrieve all products across all shops owned by the current user.
        """
        try:
            # Find all shop IDs owned by the user
            owned_shops = request.env['res.partner'].sudo().search([
                ('type', '=', 'store'),
                ('owner_user_id', '=', request.env.user.id)
            ])
            shop_ids = owned_shops.ids

            if not shop_ids:
                return request.make_json_response({'data': []}, status=200)

            domain = [('shop_id', 'in', shop_ids)]
            products = request.env['product.template'].sudo().search(domain, order="id desc")
            
            data = [self._get_product_details(p) for p in products]
            return request.make_json_response({'data': data}, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product", type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def product_create(self, shop_id, **kw):
        """
        Create a new product for a specific shop. Only the shop owner can create products for their shop.
        Expects JSON or form body with: name (required); code, description, sale_price, category_id, image (optional).
        Optional variant/attribute: variant_ids (list of attribute IDs), or attribute_lines (list of { attribute_id, value_ids }).
        """
        try:
            # Parse request data: JSON or form (with optional file for image)
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    if hasattr(request, 'get_json_data'):
                        data = request.get_json_data() or {}
                    elif request.httprequest.data:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                    else:
                        data = {}
                except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
                    data = {}
                files = {}
            else:
                data = dict(request.httprequest.form)
                files = request.httprequest.files or {}

            # Validate shop exists (verify_ownership already ensured user owns it)
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create product",
                    "statusCode": 404,
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)

            # Required field: name
            name = (data.get('name') or '').strip()
            if not name:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create product",
                    "statusCode": 400,
                    "errors": [{"name": "name", "message": "Product name is required"}]
                }, status=400)

            # Build product values (Always service for e-menu)
            create_vals = {
                'name': name,
                'shop_id': shop_id,
                'type': 'service',
            }

            if data.get('code') is not None or data.get('default_code') is not None:
                create_vals['default_code'] = (data.get('code') or data.get('default_code') or '').strip()
            if data.get('description') is not None:
                create_vals['description'] = data.get('description') or ''
            if data.get('sale_price') is not None or data.get('list_price') is not None:
                try:
                    create_vals['list_price'] = float(data.get('sale_price') or data.get('list_price') or 0)
                except (TypeError, ValueError):
                    create_vals['list_price'] = 0.0
            if data.get('category_id') is not None or data.get('categ_id') is not None:
                try:
                    categ_id = int(data.get('category_id') or data.get('categ_id') or 0)
                    if categ_id and request.env['product.category'].sudo().browse(categ_id).exists():
                        create_vals['categ_id'] = categ_id
                except (TypeError, ValueError):
                    pass

            # Image: from file upload or base64 in JSON
            image_file = files.get('image')
            image_data = data.get('image')
            
            if image_file:
                try:
                    content = image_file.read()
                    if content:
                        create_vals['image_1920'] = base64.b64encode(content).decode('utf-8')
                except Exception:
                    pass
            elif isinstance(image_data, str) and image_data.startswith('data:'):
                try:
                    raw = image_data.split(',', 1)[-1] if ',' in image_data else image_data
                    if raw and len(raw) > 10:
                        create_vals['image_1920'] = raw
                except Exception:
                    pass

            product = request.env['product.template'].sudo().create(create_vals)

            # Optional: attach variants (attributes) to the product
            AttributeLine = request.env['product.template.attribute.line'].sudo()
            attribute_lines_to_create = []  # list of (attribute_id, value_ids)

            def _parse_ids(val):
                if val is None:
                    return []
                if isinstance(val, (int, float)):
                    return [int(val)]
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except (ValueError, TypeError):
                        return []
                try:
                    return [int(x) for x in val if x is not None]
                except (TypeError, ValueError):
                    return []

            # variant_ids: list of attribute IDs — use all values for each attribute
            variant_ids_raw = data.get('variant_ids') or data.get('variant_id')
            seen_attr_ids = set()
            if variant_ids_raw is not None:
                variant_ids_raw = _parse_ids(variant_ids_raw)
                for attr_id in variant_ids_raw:
                    if attr_id in seen_attr_ids:
                        continue
                    attr = request.env['product.attribute'].sudo().browse(attr_id)
                    # Reject attributes that don't exist, have no shop_id (global), or belong to a different shop
                    if not attr.exists() or not attr.shop_id or attr.shop_id.id != shop_id:
                        continue
                    values = request.env['product.attribute.value'].sudo().search([
                        ('attribute_id', '=', attr_id)
                    ])
                    if values:
                        seen_attr_ids.add(attr_id)
                        attribute_lines_to_create.append((attr_id, values.ids))

            # attribute_lines: list of { attribute_id, value_ids } — explicit values per attribute
            attr_lines_raw = data.get('attribute_lines') or data.get('attribute_line_ids') or []
            if isinstance(attr_lines_raw, str):
                try:
                    attr_lines_raw = json.loads(attr_lines_raw)
                except (ValueError, TypeError):
                    attr_lines_raw = []
            if not isinstance(attr_lines_raw, list):
                attr_lines_raw = []
            for raw in attr_lines_raw:
                if not isinstance(raw, dict):
                    continue
                try:
                    attr_id = int(raw.get('attribute_id', 0) or 0)
                except (TypeError, ValueError):
                    continue
                if not attr_id:
                    continue
                attr = request.env['product.attribute'].sudo().browse(attr_id)
                # Reject attributes that don't exist, have no shop_id (global), or belong to a different shop
                if not attr.exists() or not attr.shop_id or attr.shop_id.id != shop_id:
                    continue
                val_ids = _parse_ids(raw.get('value_ids'))
                if not val_ids:
                    continue
                # Ensure values belong to this attribute
                valid = request.env['product.attribute.value'].sudo().search([
                    ('id', 'in', val_ids), ('attribute_id', '=', attr_id)
                ]).ids
                if valid:
                    # Merge with existing line for same attribute from variant_ids
                    existing = next((x for x in attribute_lines_to_create if x[0] == attr_id), None)
                    if existing:
                        merged = list(set(existing[1]) | set(valid))
                        attribute_lines_to_create = [(a, v) for a, v in attribute_lines_to_create if a != attr_id]
                        attribute_lines_to_create.append((attr_id, merged))
                    else:
                        attribute_lines_to_create.append((attr_id, valid))
            for attr_id, value_ids in attribute_lines_to_create:
                AttributeLine.create({
                    'product_tmpl_id': product.id,
                    'attribute_id': attr_id,
                    'value_ids': [(6, 0, value_ids)],
                })

            product_data = self._get_product_details(product)
            product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
            product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
            product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
            return request.make_json_response({'data': product_data}, status=201)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create product",
                "statusCode": 500,
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>', type="http", auth="public", methods=["GET"], cors="*", csrf=False)
    def product_detail(self, shop_id, product_id, **kw):
        """Get a single product by ID for a specific shop."""
        try:
            product = request.env['product.template'].sudo().search([
                ('id', '=', product_id), ('shop_id', '=', shop_id)
            ], limit=1)
            if not product:
                return request.make_json_response({'error': 'Product not found'}, status=404)
            product_data = self._get_product_details(product)
            product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
            product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
            product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
            return request.make_json_response({'data': product_data}, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>', type="http", auth="angkit", methods=["PUT"], cors="*", csrf=False)
    @verify_ownership(entity_type='product')
    def product_update(self, shop_id, product_id, **kw):
        """Update an existing product for a specific shop. PUT requires name."""
        try:
            # Parse request data: JSON or form
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    if hasattr(request, 'get_json_data'):
                        data = request.get_json_data() or {}
                    elif request.httprequest.data:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                    else:
                        data = {}
                except Exception:
                    data = {}
                files = {}
            else:
                data = dict(request.httprequest.form)
                files = request.httprequest.files or {}

            product = request.env['product.template'].sudo().browse(product_id)
            
            # Required field for PUT: name
            name = (data.get('name') or '').strip()
            if not name:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update product",
                    "statusCode": 400,
                    "errors": [{"name": "name", "message": "Product name is required"}]
                }, status=400)

            # Build update values (Force type to service)
            update_vals = {
                'name': name,
                'type': 'service',
            }

            if 'code' in data or 'default_code' in data:
                update_vals['default_code'] = (data.get('code') or data.get('default_code') or '').strip()
            
            if 'description' in data:
                update_vals['description'] = data.get('description') or ''

            if data.get('sale_price') is not None or data.get('list_price') is not None:
                try:
                    update_vals['list_price'] = float(data.get('sale_price') or data.get('list_price') or 0)
                except (TypeError, ValueError):
                    pass

            if data.get('category_id') is not None or data.get('categ_id') is not None:
                try:
                    categ_id = int(data.get('category_id') or data.get('categ_id') or 0)
                    if categ_id and request.env['product.category'].sudo().browse(categ_id).exists():
                        update_vals['categ_id'] = categ_id
                except (TypeError, ValueError):
                    pass

            # Image handling: ONLY update if it's a new file or a valid base64 string
            image_file = files.get('image')
            image_data = data.get('image')
            
            if image_file:
                try:
                    content = image_file.read()
                    if content:
                        update_vals['image_1920'] = base64.b64encode(content).decode('utf-8')
                except Exception:
                    pass
            elif isinstance(image_data, str) and image_data.startswith('data:'):
                try:
                    # Extract and validate base64 part
                    raw = image_data.split(',', 1)[-1] if ',' in image_data else image_data
                    if raw and len(raw) > 10: # Basic check for content
                        update_vals['image_1920'] = raw
                except Exception:
                    pass
            elif image_data is False or image_data == 'false' or image_data == '':
                # Explicitly clear the image if empty string or false is sent
                # But only if we are in a PUT request (full update)
                if request.httprequest.method == 'PUT':
                     update_vals['image_1920'] = False

            product.write(update_vals)
            
            product_data = self._get_product_details(product)
            product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
            product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
            product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
            return request.make_json_response({'data': product_data}, status=200)
        except Exception as e:
            import traceback
            return request.make_json_response({
                "status": "error",
                "message": f"Failed to update product: {str(e)}",
                "statusCode": 500,
                "traceback": traceback.format_exc(),
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>', type="http", auth="angkit", methods=["PATCH"], cors="*", csrf=False)
    @verify_ownership(entity_type='product')
    def product_patch(self, shop_id, product_id, **kw):
        """Partially update an existing product for a specific shop."""
        try:
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    if hasattr(request, 'get_json_data'):
                        data = request.get_json_data() or {}
                    elif request.httprequest.data:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                    else:
                        data = {}
                except Exception:
                    data = {}
                files = {}
            else:
                data = dict(request.httprequest.form)
                files = request.httprequest.files or {}

            product = request.env['product.template'].sudo().browse(product_id)
            update_vals = {}

            if 'name' in data:
                update_vals['name'] = data['name'].strip()
            
            # Always ensure type is service
            update_vals['type'] = 'service'
            if 'description' in data:
                update_vals['description'] = data['description'] or ''
            if 'code' in data or 'default_code' in data:
                update_vals['default_code'] = (data.get('code') or data.get('default_code') or '').strip()
            if 'sale_price' in data or 'list_price' in data:
                try:
                    update_vals['list_price'] = float(data.get('sale_price') or data.get('list_price'))
                except (TypeError, ValueError):
                    pass
            if 'category_id' in data or 'categ_id' in data:
                try:
                    categ_id = int(data.get('category_id') or data.get('categ_id'))
                    if categ_id and request.env['product.category'].sudo().browse(categ_id).exists():
                        update_vals['categ_id'] = categ_id
                except (TypeError, ValueError):
                    pass

            image_file = files.get('image')
            image_data = data.get('image')
            
            if image_file:
                try:
                    content = image_file.read()
                    if content:
                        update_vals['image_1920'] = base64.b64encode(content).decode('utf-8')
                except Exception:
                    pass
            elif isinstance(image_data, str) and image_data.startswith('data:'):
                try:
                    raw = image_data.split(',', 1)[-1] if ',' in image_data else image_data
                    if raw and len(raw) > 10:
                        update_vals['image_1920'] = raw
                except Exception:
                    pass
            elif image_data == '' or image_data is False:
                update_vals['image_1920'] = False

            if update_vals:
                product.write(update_vals)

            product_data = self._get_product_details(product)
            return request.make_json_response({'data': product_data}, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to patch product",
                "statusCode": 500,
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>', type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='product')
    def product_delete(self, shop_id, product_id, **kw):
        """Delete a product from a specific shop."""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            product.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete product",
                "statusCode": 500,
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/attribute-line', type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def product_attribute_line_create(self, shop_id, product_id, **kw):
        """Link an attribute (with all its current values) to an existing product."""
        try:
            data = request.httprequest.form
            try:
                attribute_id = int(data.get('attribute_id', 0))
            except (TypeError, ValueError):
                attribute_id = 0
            if not attribute_id:
                return request.make_json_response({
                    'status': 'error', 'message': 'attribute_id is required'
                }, status=400)
            product = request.env['product.template'].sudo().search([
                ('id', '=', product_id), ('shop_id', '=', shop_id)
            ], limit=1)
            if not product:
                return request.make_json_response({'status': 'error', 'message': 'Product not found'}, status=404)
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', attribute_id), ('shop_id', '=', shop_id)
            ], limit=1)
            if not attribute:
                return request.make_json_response({'status': 'error', 'message': 'Attribute not found'}, status=404)
            existing = request.env['product.template.attribute.line'].sudo().search([
                ('product_tmpl_id', '=', product_id), ('attribute_id', '=', attribute_id)
            ], limit=1)
            if existing:
                return request.make_json_response({
                    'status': 'ok', 'message': 'Attribute already linked to this product'
                }, status=200)
            values = request.env['product.attribute.value'].sudo().search([('attribute_id', '=', attribute_id)])
            if not values:
                return request.make_json_response({
                    'status': 'error',
                    'message': 'This attribute has no values yet. Add values to the attribute before linking it to a product.'
                }, status=400)
            request.env['product.template.attribute.line'].sudo().create({
                'product_tmpl_id': product_id,
                'attribute_id': attribute_id,
                'value_ids': [(6, 0, values.ids)],  # all current values; user removes unwanted ones per-product
            })
            return request.make_json_response({'message': 'Attribute linked to product'}, status=201)
        except Exception as e:
            return request.make_json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/attribute-line/<int:line_id>', type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def product_attribute_line_delete(self, shop_id, product_id, line_id, **kw):
        """Remove an attribute line from a product (unlinks the attribute from this product only)."""
        try:
            line = request.env['product.template.attribute.line'].sudo().search([
                ('id', '=', line_id),
                ('product_tmpl_id', '=', product_id),
                ('product_tmpl_id.shop_id', '=', shop_id),
            ], limit=1)
            if not line:
                return request.make_json_response({'status': 'error', 'message': 'Attribute line not found'}, status=404)
            line.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/attribute-line/<int:line_id>/value', type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def product_attribute_line_value_add(self, shop_id, product_id, line_id, **kw):
        """Add an existing product.attribute.value to a product's attribute line (per-product, no global creation)."""
        try:
            data = request.httprequest.form
            try:
                value_id = int(data.get('value_id', 0))
            except (TypeError, ValueError):
                value_id = 0
            if not value_id:
                return request.make_json_response({'status': 'error', 'message': 'value_id is required'}, status=400)
            line = request.env['product.template.attribute.line'].sudo().search([
                ('id', '=', line_id),
                ('product_tmpl_id', '=', product_id),
                ('product_tmpl_id.shop_id', '=', shop_id),
            ], limit=1)
            if not line:
                return request.make_json_response({'status': 'error', 'message': 'Attribute line not found'}, status=404)
            value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not value.exists() or value.attribute_id.id != line.attribute_id.id:
                return request.make_json_response({'status': 'error', 'message': 'Value not found or does not belong to this attribute'}, status=404)
            if value in line.value_ids:
                return request.make_json_response({'status': 'error', 'message': 'Value already in this product'}, status=400)
            line.write({'value_ids': [(4, value_id)]})
            return request.make_json_response({'message': 'Value added to product'}, status=201)
        except Exception as e:
            return request.make_json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route(f'{BASE_URL}/shop/<int:shop_id>/product/<int:product_id>/attribute-line/<int:line_id>/value/<int:value_id>', type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def product_attribute_line_value_remove(self, shop_id, product_id, line_id, value_id, **kw):
        """Remove a value from a product's attribute line (does NOT delete the global product.attribute.value)."""
        try:
            line = request.env['product.template.attribute.line'].sudo().search([
                ('id', '=', line_id),
                ('product_tmpl_id', '=', product_id),
                ('product_tmpl_id.shop_id', '=', shop_id),
            ], limit=1)
            if not line:
                return request.make_json_response({'status': 'error', 'message': 'Attribute line not found'}, status=404)
            line.write({'value_ids': [(3, value_id)]})
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route(f'{BASE_URL}/product', methods=['GET'], auth='public', type="http", cors="*")
    def global_product_list(self, **kw):
        """
        Retrieve a paginated list of all products (global, not shop-specific) with search, filter, and sort capabilities.
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
                    domain.append(('list_price', '>=', price_min))  # type: ignore
                except ValueError:
                    pass
            
            if filter_price_max:
                try:
                    price_max = float(filter_price_max)
                    domain.append(('list_price', '<=', price_max))  # type: ignore
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
            total_count = request.env['product.template'].sudo().search_count(domain)
            page_count = (total_count + limit - 1) // limit
            page = min(max(1, page), page_count) if page_count > 0 else 1
            
            # Build order clause
            order_clause = f"{sort} {order}"
            
            # Fetch products
            products = request.env['product.template'].sudo().search(
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

    @http.route(f"{BASE_URL}/product/<int:product_id>", methods=['GET'], auth="public", type="http", cors="*")
    def global_product_detail(self, product_id):
        """
        Retrieve details for a specific product (global, not shop-specific).
        """
        try:
            product = request.env['product.template'].sudo().search([('id', '=', product_id)], limit=1)
            if not product:
                return request.make_json_response({'error': 'Product not found'}, status=404)
            product_data = self._get_product_details(product)
            product_data['createdAt'] = product.create_date.isoformat() if product.create_date else None
            product_data['updatedAt'] = product.write_date.isoformat() if product.write_date else None
            product_data['publishedAt'] = product.create_date.isoformat() if product.create_date else None
            response = {
                'data': product_data
            }
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/product/category", methods=['GET'], auth="public", type="http", cors="*")
    def global_product_category(self, **kw):
        """
        Retrieve a paginated list of all product categories (global, not shop-specific) with search, filter, and sort capabilities.
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/category", methods=['GET'], auth="public", type="http", cors="*")
    def category_list(self, shop_id, **kw):
        """List categories for a specific shop."""
        try:
            domain = [('shop_id', '=', shop_id)]
            categories = request.env['product.category'].sudo().search(domain)
            
            data = []
            for category in categories:
                data.append({
                    'id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id.id if category.parent_id else None,
                    'shop_id': category.shop_id.id
                })
            return request.make_json_response({'data': data}, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/category", methods=['POST'], auth="angkit", type="http", cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def category_create(self, shop_id, **kw):
        """Create a category for a shop."""
        try:
            data = json.loads(request.httprequest.data) if request.httprequest.data else {}
            name = data.get('name')
            if not name:
                return request.make_json_response({'error': 'Name is required'}, status=400)
                
            category = request.env['product.category'].sudo().create({
                'name': name,
                'shop_id': shop_id,
                'parent_id': data.get('parent_id')
            })
            return request.make_json_response({
                'data': {'id': category.id, 'name': category.name}
            }, status=201)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/category/<int:cate_id>", methods=['PUT'], auth="angkit", type="http", cors="*", csrf=False)
    @verify_ownership(entity_type='category')
    def category_update(self, shop_id, cate_id, **kw):
        """Update a shop category."""
        try:
            data = json.loads(request.httprequest.data) if request.httprequest.data else {}
            category = request.env['product.category'].sudo().browse(cate_id)
            
            vals = {}
            if 'name' in data: vals['name'] = data['name']
            if 'parent_id' in data: vals['parent_id'] = data['parent_id']
            
            category.write(vals)
            return request.make_json_response({
                'data': {'id': category.id, 'name': category.name}
            }, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/category/<int:cate_id>", methods=['DELETE'], auth="angkit", type="http", cors="*", csrf=False)
    @verify_ownership(entity_type='category')
    def category_delete(self, shop_id, cate_id, **kw):
        """Delete a shop category."""
        try:
            category = request.env['product.category'].sudo().browse(cate_id)
            category.unlink()
            return request.make_json_response({'data': True}, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/product/variant", methods=['GET'], auth="public", type="http", cors="*")
    def global_product_variant(self, **kw):
        """
        Retrieve a paginated list of all product attributes (global, not shop-specific) with search, filter, and sort capabilities.
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

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["GET"], cors="*", csrf=False)
    def variant_list(self, shop_id, **kw):
        """
        Retrieve all product variants for a specific shop with search, filter, and sort capabilities.
        """
        try:
            # Verify shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({'error': 'Shop not found'}, status=404)
            
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
            
            # Build domain — filter by shop_id only.
            # create_uid is unreliable because attributes are created via sudo() (create_uid = superuser).
            # Shop ownership is verified via verify_ownership on write endpoints; listing is scoped to the shop.
            domain = [
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
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant", type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def variant_create(self, shop_id, **kw):
        """
        Create a new product variant for a specific shop.
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
                
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)
            
            if data['create_variant'] not in VALID_CREATE_VARIANTS:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": [{"name": "create_variant", "message": f"Invalid create_variant value. Must be one of: {', '.join(VALID_CREATE_VARIANTS)}"}]
                }, status=400)
            
            if data['display_type'] not in VALID_DISPLAY_TYPES:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": [{"name": "display_type", "message": f"Invalid display_type value. Must be one of: {', '.join(VALID_DISPLAY_TYPES)}"}]
                }, status=400)
            
            if request.env['product.attribute'].sudo().search_count([('name', '=', data['name']), ('shop_id', '=', shop_id)], limit=1):
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant",
                    "statusCode": "400",
                    "errors": [{"name": "name", "message": f"Attribute with name {data['name']} already exists"}]
                }, status=400)
            
            variant_create_data = {
                'name': data['name'],
                'create_variant': data['create_variant'],
                'display_type': data['display_type'],
                'shop_id': shop_id
            }
            if variant_create_data.get('display_type') == 'multi':
                variant_create_data['create_variant'] = 'no_variant'
            attribute = request.env['product.attribute'].sudo().create(variant_create_data)
            return request.make_json_response(self._attribute_to_dict(attribute), status=201)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PUT"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant')
    def variant_update(self, shop_id, variant_id, **kw):
        """
        Update an existing product variant for a specific shop.
        """
        try:
            # Get request data - try JSON first, fallback to form data
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    if hasattr(request, 'get_json_data'):
                        data = request.get_json_data() or {}
                    else:
                        if request.httprequest.data:
                            data = json.loads(request.httprequest.data.decode('utf-8'))
                        else:
                            data = {}
                except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
                    data = {}
            else:
                data = dict(request.httprequest.form)

            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)

            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "404",
                    "errors": [{"name": "variant_id", "message": "Attribute not found"}]
                }, status=404)

            # Define valid fields and allowed values
            VALID_FIELDS = {'name', 'create_variant', 'display_type'}
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}

            # PUT requires all fields
            missing_fields = VALID_FIELDS - set(data.keys())
            if missing_fields:
                errors = []
                for field in missing_fields:
                    errors.append({"name": field, "message": f"{field} is required"})
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)

            # Filter only valid fields and prepare update dict
            update_vals = {}

            # Validate and process name
            name = data['name']
            if isinstance(name, str):
                name = name.strip()
            if not name:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "400",
                    "errors": [{"name": "name", "message": "Variant name is required"}]
                }, status=400)
            if name != attribute.name:
                if request.env['product.attribute'].sudo().search_count([
                    ('shop_id', '=', shop_id),
                    ('name', '=', name),
                    ('id', '!=', attribute.id)
                ]):
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to update variant",
                        "statusCode": "400",
                        "errors": [{"name": "name", "message": f"Attribute with name '{name}' already exists"}]
                    }, status=400)
            update_vals['name'] = name

            # Validate and process create_variant
            create_variant = data['create_variant']
            if isinstance(create_variant, str):
                create_variant = create_variant.strip()
            if create_variant not in VALID_CREATE_VARIANTS:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "400",
                    "errors": [{"name": "create_variant", "message": f"Invalid create_variant value. Must be one of: {', '.join(VALID_CREATE_VARIANTS)}"}]
                }, status=400)
            update_vals['create_variant'] = create_variant

            # Validate and process display_type
            display_type = data['display_type']
            if isinstance(display_type, str):
                display_type = display_type.strip()
            if display_type not in VALID_DISPLAY_TYPES:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant",
                    "statusCode": "400",
                    "errors": [{"name": "display_type", "message": f"Invalid display_type value. Must be one of: {', '.join(VALID_DISPLAY_TYPES)}"}]
                }, status=400)
            update_vals['display_type'] = display_type

            # Auto-set create_variant for multi display type
            if display_type == 'multi':
                update_vals['create_variant'] = 'no_variant'

            # Write only validated fields
            attribute.write(update_vals)
            return request.make_json_response(self._attribute_to_dict(attribute), status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["PATCH"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant')
    def variant_patch(self, shop_id, variant_id, **kw):
        """
        Partially update an existing product variant for a specific shop.
        """
        try:
            # Get request data - try JSON first, fallback to form data
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    # Try to get JSON data using get_json_data if available
                    if hasattr(request, 'get_json_data'):
                        data = request.get_json_data() or {}
                    else:
                        # Fallback: parse JSON from request body
                        if request.httprequest.data:
                            data = json.loads(request.httprequest.data.decode('utf-8'))
                        else:
                            data = {}
                except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
                    data = {}
            else:
                data = dict(request.httprequest.form)
            
            # Validate shop exists
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            # Validate attribute exists
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "404",
                    "errors": [{"name": "variant_id", "message": "Attribute not found"}]
                }, status=404)
            
            # Define valid fields that can be updated
            VALID_FIELDS = {'name', 'create_variant', 'display_type'}
            VALID_CREATE_VARIANTS = {'no_variant', 'always'}
            VALID_DISPLAY_TYPES = {'multi', 'radio'}
            
            # Filter only valid fields and prepare update dict
            update_vals = {}
            
            # Validate and process name
            if 'name' in data:
                name = data['name']
                if isinstance(name, str):
                    name = name.strip()
                    if name and name != attribute.name:
                        # Check for duplicate names
                        if request.env['product.attribute'].sudo().search_count([
                            ('shop_id', '=', shop_id), 
                            ('name', '=', name),
                            ('id', '!=', attribute.id)
                        ]):
                            return request.make_json_response({
                                "status": "error",
                                "message": "Failed to patch variant",
                                "statusCode": "400",
                                "errors": [{"name": "name", "message": f"Attribute with name '{name}' already exists"}]
                            }, status=400)
                        update_vals['name'] = name
            
            # Validate and process create_variant
            if 'create_variant' in data:
                create_variant = data['create_variant']
                if isinstance(create_variant, str):
                    create_variant = create_variant.strip()
                if create_variant not in VALID_CREATE_VARIANTS:
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to patch variant",
                        "statusCode": "400",
                        "errors": [{"name": "create_variant", "message": f"Invalid create_variant value. Must be one of: {', '.join(VALID_CREATE_VARIANTS)}"}]
                    }, status=400)
                update_vals['create_variant'] = create_variant
            
            # Validate and process display_type
            if 'display_type' in data:
                display_type = data['display_type']
                if isinstance(display_type, str):
                    display_type = display_type.strip()
                if display_type not in VALID_DISPLAY_TYPES:
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to patch variant",
                        "statusCode": "400",
                        "errors": [{"name": "display_type", "message": f"Invalid display_type value. Must be one of: {', '.join(VALID_DISPLAY_TYPES)}"}]
                    }, status=400)
                update_vals['display_type'] = display_type
                
                # Auto-set create_variant for multi display type
                if display_type == 'multi':
                    update_vals['create_variant'] = 'no_variant'
            
            # If no valid fields to update, return error
            if not update_vals:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch variant",
                    "statusCode": "400",
                    "errors": [{"name": "general", "message": "No valid fields provided for update"}]
                }, status=400)
            
            # Write only validated fields
            attribute.write(update_vals)
            
            return request.make_json_response(self._attribute_to_dict(attribute), status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to patch variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/<int:variant_id>", type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant')
    def variant_delete(self, shop_id, variant_id, **kw):
        """
        Delete a product variant from a specific shop.
        """
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete variant",
                    "statusCode": "404",
                    "errors": [{"name": "shop_id", "message": "Shop not found"}]
                }, status=404)
            
            attribute = request.env['product.attribute'].sudo().search([
                ('id', '=', variant_id),
                ('shop_id', '=', shop_id),
            ], limit=1)
            if not attribute:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete variant",
                    "statusCode": "404",
                    "errors": [{"name": "variant_id", "message": "Attribute not found"}]
                }, status=404)

            attribute.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete variant",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/<int:variant_id>/value", type="http", auth="angkit", methods=["GET"], cors="*", csrf=False)
    def variant_value_list(self, shop_id, variant_id, **kw):
        """
        Retrieve all values for a specific product variant in a shop.
        """
        try:
            shop = request.env['res.partner'].sudo().search([('id', '=', shop_id), ('type', '=', 'store')], limit=1)
            if not shop:
                return request.make_json_response({'error': 'Shop not found'}, status=404)
            attribute = request.env['product.attribute'].sudo().search([('id', '=', variant_id), ('shop_id', '=', shop_id)], limit=1)
            if not attribute:
                return request.make_json_response({'error': 'Attribute not found'}, status=404)
            
            # Parse query parameters
            search = request.httprequest.args.get('search', '').strip()
            sort = request.httprequest.args.get('sort', 'id')
            order = request.httprequest.args.get('order', 'asc').lower()
            
            # Validate sort field
            valid_sort_fields = {'id', 'name', 'default_extra_price', 'create_date'}
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
                    'extra_price': value.default_extra_price,
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
            return request.make_json_response(response, status=200)
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value", type="http", auth="angkit", methods=["POST"], cors="*", csrf=False)
    @verify_ownership(entity_type='shop')
    def variant_value_create(self, shop_id, **kw):
        """
        Create new variant values for a product attribute.
        """
        try:
            data = request.httprequest.form
            if 'attribute_id' not in data or 'values' not in data:
                errors = []
                if 'attribute_id' not in data:
                    errors.append({"name": "attribute_id", "message": "Attribute ID is required"})
                if 'values' not in data:
                    errors.append({"name": "values", "message": "Values are required"})
                
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "400",
                    "errors": errors
                }, status=400)
            
            attribute = request.env['product.attribute'].sudo().browse(int(data['attribute_id']))
            if not attribute.exists():
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "404",
                    "errors": [{"name": "attribute_id", "message": f"Attribute with ID {data['attribute_id']} not found"}]
                }, status=404)
            
            if attribute.shop_id.id != shop_id:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "400",
                    "errors": [{"name": "attribute_id", "message": "Attribute doesn't belong to this shop"}]
                }, status=400)
            
            try:
                values_data = json.loads(data['values'])
                if not isinstance(values_data, list):
                    return request.make_json_response({
                        "status": "error",
                        "message": "Failed to create variant values",
                        "statusCode": "400",
                        "errors": [{"name": "values", "message": "Values must be a list"}]
                    }, status=400)
                
                values_to_create = [{
                    'default_extra_price': value.get('extra_price', 0.0),
                    'name': value['name'],
                    'attribute_id': attribute.id,
                } for value in values_data if 'name' in value]
                created_values = request.env['product.attribute.value'].sudo().create(values_to_create)

                # If product_id is provided, also add the new values to that product's attribute line
                product_id_raw = data.get('product_id')
                if product_id_raw and created_values:
                    try:
                        product_id_val = int(product_id_raw)
                        line = request.env['product.template.attribute.line'].sudo().search([
                            ('product_tmpl_id', '=', product_id_val),
                            ('product_tmpl_id.shop_id', '=', shop_id),
                            ('attribute_id', '=', attribute.id),
                        ], limit=1)
                        if line:
                            line.write({'value_ids': [(4, vid) for vid in created_values.ids]})
                    except (TypeError, ValueError):
                        pass

                return request.make_json_response({'message': 'Attribute values created successfully'}, status=201)
            except json.JSONDecodeError:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to create variant values",
                    "statusCode": "400",
                    "errors": [{"name": "values", "message": "Invalid JSON format for values"}]
                }, status=400)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to create variant values",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["PUT"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant_value')
    def variant_value_update(self, shop_id, value_id, **kw):
        """
        Update an existing variant value.
        """
        try:
            data = request.httprequest.form
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant value",
                    "statusCode": "404",
                    "errors": [{"name": "value_id", "message": "Variant value not found"}]
                }, status=404)
            
            update_fields = {}
            if 'name' in data:
                update_fields['name'] = data['name']
            if 'price_extra' in data:
                update_fields['default_extra_price'] = data['price_extra']

            if not update_fields:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to update variant value",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)
            
            variant_value.write(update_fields)
            return request.make_json_response({'message': 'Variant value updated successfully'}, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to update variant value",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["PATCH"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant_value')
    def variant_value_patch(self, shop_id, value_id, **kw):
        """
        Partially update an existing variant value.
        """
        try:
            data = request.httprequest.form
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch variant value",
                    "statusCode": "404",
                    "errors": [{"name": "value_id", "message": "Variant value not found"}]
                }, status=404)
            
            update_fields = {}
            if 'name' in data:
                update_fields['name'] = data['name']
            if 'price_extra' in data:
                update_fields['default_extra_price'] = data['price_extra']

            if not update_fields:
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to patch variant value",
                    "statusCode": "400",
                    "errors": [{"name": "fields", "message": "No valid fields to update"}]
                }, status=400)
            
            variant_value.write(update_fields)
            return request.make_json_response({'message': 'Variant value patched successfully'}, status=200)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to patch variant value",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/shop/<int:shop_id>/product/variant/value/<int:value_id>", type="http", auth="angkit", methods=["DELETE"], cors="*", csrf=False)
    @verify_ownership(entity_type='variant_value')
    def variant_value_delete(self, shop_id, value_id, **kw):
        """
        Delete a variant value.
        """
        try:
            variant_value = request.env['product.attribute.value'].sudo().browse(value_id)
            if not variant_value.exists():
                return request.make_json_response({
                    "status": "error",
                    "message": "Failed to delete variant value",
                    "statusCode": "404",
                    "errors": [{"name": "value_id", "message": "Variant value not found"}]
                }, status=404)
            
            variant_value.unlink()
            return request.make_json_response('', status=204)
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": "Failed to delete variant value",
                "statusCode": "500",
                "errors": [{"name": "general", "message": str(e)}]
            }, status=500)

    @http.route(f"{BASE_URL}/image/add", auth="angkit", type="http", methods=["POST"], cors="*", csrf=False)
    def image_add(self, quality=0, width=0, height=0, res_id=False, res_model='ir.ui.view', **kw):
        """
        Upload, validate, process, and store an image with automatic WebP conversion.
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

            # Read and encode image (datas expects base64)
            image_data = base64.b64encode(image_file.read())

            # Create attachment
            attachment = request.env['ir.attachment'].sudo().create({
                'name': image_file.filename,
                'datas': image_data,
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

