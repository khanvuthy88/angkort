
import json
import logging

from odoo import http
from odoo.http import request, route
from odoo.tools import config

_logger = logging.getLogger(__name__)



BASE_URL = '/angkort/api/v1'

class ShopController(http.Controller):

    @http.route(f'{BASE_URL}/store', type='http', auth='public', methods=['GET'])
    def get_partners(self, **kwargs):
        # Extract query parameters
        name_filter = kwargs.get('name', False)
        order_by = kwargs.get('order_by', 'name asc')
        page = int(kwargs.get('page', 1))
        page_size = int(kwargs.get('page_size', 10))

        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:  # Upper limit for safety
            page_size = 10

        # Calculate offset
        offset = (page - 1) * page_size

        # Build domain for search
        domain = []
        if name_filter:
            domain.append(('name', 'ilike', f'%{name_filter}%'))

        try:
            # Get total count for pagination metadata
            total_count = request.env['res.partner'].sudo().search_count(domain)

            # Search partners with pagination
            partners = request.env['res.partner'].sudo().search(
                domain,
                order=order_by,
                offset=offset,
                limit=page_size
            )

            # Prepare response data
            partner_data = [{
                'id': partner.id,
                'name': partner.name,
                'email': partner.email or '',
                'phone': partner.phone or '',
                'street': partner.street or '',
                'city': partner.city or '',
                'country_id': partner.country_id.name or '',
                'image_url': '' if not partner.image_1920 else f'/web/image/res.partner/{partner.id}/image_1920'
            } for partner in partners]

            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size

            return http.Response(
                json.dumps({
                    'status': 'success',
                    'data': partner_data,
                    'pagination': {
                        'current_page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': total_pages
                    }
                }),
                content_type='application/json',
                status=200
            )

        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'message': str(e)
                }),
                content_type='application/json',
                status=500
            )