# -*- coding: utf-8 -*-
import base64
import json
import re
import uuid
from datetime import datetime

import requests

from odoo import http, tools
from odoo.exceptions import UserError
from odoo.http import request
from odoo import fields, _

from odoo.tools.mimetypes import guess_mimetype

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


class EMenu(http.Controller):

    def _clean_context(self):
        # avoid allowed_company_ids which may erroneously restrict based on website
        context = dict(request.context)
        context.pop('allowed_company_ids', None)
        request.update_env(context=context)

    def _image_to_webp(self, attachment, res_model=None, res_id=None, name=None, data=None, original_id=None,
                       mimetype=None, alt_data=None):
        """
        Creates a modified copy of an attachment and returns its image_src to be
        inserted into the DOM.
        """
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
            # Don't keep url if modifying static attachment because static images
            # are only served from disk and don't fallback to attachments.
            if re.match(r'^/\w+/static/', attachment.url):
                attachment.url = None
            # Uniquify url by adding a path segment with the id before the name.
            # This allows us to keep the unsplash url format so it still reacts
            # to the unsplash beacon.
            else:
                url_fragments = attachment.url.split('/')
                url_fragments.insert(-1, str(attachment.id))
                attachment.url = '/'.join(url_fragments)
        if attachment.public:
            return attachment.image_src
        attachment.generate_access_token()
        return '%s?access_token=%s' % (attachment.image_src, attachment.access_token)

    def _attachment_create(self, name='', data=False, url=False, res_id=False, res_model='ir.ui.view'):
        """Create and return a new attachment."""
        IrAttachment = request.env['ir.attachment']

        if name.lower().endswith('.bmp'):
            # Avoid mismatch between content type and mimetype, see commit msg
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
            # The code issues a HEAD request to retrieve headers from the URL.
            # This approach is beneficial when the URL doesn't conclude with an
            # image extension. By verifying the MIME type, the code ensures that
            # only supported image types are incorporated into the data.
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                mime_type = response.headers['content-type']
                if mime_type in SUPPORTED_IMAGE_MIMETYPES:
                    attachment_data['mimetype'] = mime_type
        else:
            raise UserError(_("You need to specify either data or url to create an attachment."))

        # Despite the user having no right to create an attachment, he can still
        # create an image attachment through some flows
        if (
                not request.env.is_admin()
                and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
        ):
            attachment = IrAttachment.sudo().create(attachment_data)
            # When portal users upload an attachment with the wysiwyg widget,
            # the access token is needed to use the image in the editor. If
            # the attachment is not public, the user won't be able to generate
            # the token, so we need to generate it using sudo
            if not attachment_data['public']:
                attachment.sudo().generate_access_token()
        else:
            attachment = IrAttachment.create(attachment_data)

        return attachment

    @http.route(f"{BASE_URL}/product/category", auth="public", type="json", cors=False)
    def product_category(self):
        """
        Returns a list of product categories in JSON format.

        The route for this endpoint is `BASE_URL/product/category`, and it is publicly accessible.
        """
        categories = request.env['product.category'].sudo().search([])
        return [{
            'id': category.id,
            'name': category.name
        } for category in categories]

    @http.route(f"{BASE_URL}/image/add", auth="user", type="http", methods=["POST"], cores=False)
    def image_add(self, quality=0, width=0, height=0, res_id=False, res_model='ir.ui.view', **kw):
        try:
            image_file = request.httprequest.files['image']
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

            data = base64.b64decode(image_data)

            format_error_msg = _("Uploaded image's format is not supported. Try with: %s",
                                 ', '.join(SUPPORTED_IMAGE_MIMETYPES.values()))
        except Exception as e:
            return request.make_json_response({'error': str(e)}, status=400)

        try:
            data = tools.image_process(data, size=(width, height), quality=quality, verify_resolution=True)
            mimetype = guess_mimetype(data)
            if mimetype not in SUPPORTED_IMAGE_MIMETYPES:
                return request.make_json_response({'error': format_error_msg}, status=400)

            name = f'{image_file.filename}%s-%s%s' % (
                datetime.now().strftime('%Y%m%d%H%M%S'),
                str(uuid.uuid4())[:6],
                SUPPORTED_IMAGE_MIMETYPES[mimetype],
            )
        except UserError:
            # considered as an image by the browser file input, but not
            # recognized as such by PIL, eg .webp
            return request.make_json_response({'error': format_error_msg}, status=400)
        except ValueError as e:
            return request.make_json_response({'error': e.args[0]}, status=400)

        self._clean_context()
        attachment = self._attachment_create(name=name, data=data, res_id=res_id, res_model=res_model)
        image_webp_url = self._image_to_webp(attachment=attachment, mimetype="image/webp", data=attachment.datas)
        return request.make_json_response({
            'image': image_webp_url
        })

    @http.route(f'{BASE_URL}/product/list', auth='public', type="json", cors=False)
    def product_list(self):
        """
        Returns a list of products with details such as ID, name, code, sale price,
        and category information in JSON format.

        The route for this endpoint is `BASE_URL/product/list`, and it is publicly accessible.
        """
        products = request.env['product.template'].sudo().search([])
        return [{
            'id': product.id,
            'name': product.name,
            'code': product.default_code,
            'description': product.description,
            'sale_price': product.list_price,
            'image': product.image_1920,
            'category': {
                'id': product.categ_id.id,
                'name': product.categ_id.name
            }
        } for product in products]

    @http.route(f"{BASE_URL}/sale/list", auth="public", type="json")
    def sale_order(self):

        """
        Returns a list of sales orders with details such as ID, name, state, order date,
        customer information, salesman information, sales team information, order lines,
        and total in JSON format.

        The route for this endpoint is `BASE_URL/sale/list`, and it is publicly accessible.
        """
        sale_orders = request.env['sale.order'].sudo().search([])
        return [{
            'id': sale.id,
            'name': sale.name,
            'state': SALE_STATE.get(sale.state),
            'order_date': sale.date_order.strftime('%d-%m-%Y'),
            'customer': sale.partner_id.name,
            'salesman': sale.user_id.name,
            'sale_team': sale.team_id.name,
            'order_lines': [{
                'product': {
                    'id': line.product_id.id,
                    'name': line.product_id.name
                },
                'qty': line.product_uom_qty,
                'unit_price': line.price_unit,
                'total': line.price_subtotal
            } for line in sale.order_line],
            'total': sale.tax_totals
        } for sale in sale_orders]

    @http.route(f"{BASE_URL}/order/new", auth="public", type="json", methods=["POST"], cors=False)
    def new_order(self):
        data = json.loads(request.httprequest.data.decode('utf-8'))
        partner_id = data['params'].get('customer_id', 0)
        order_date = data['params'].get('order_date', '')
        order_date = fields.Datetime.now()
        order_line = data['params'].get('order_line', [])
        sale_order = request.env['sale.order'].sudo().create({
            'partner_id': partner_id,
            'date_order': order_date,
            'order_line': [
                (0, 0, {
                    'product_id': line['product_id'],
                    'product_uom_qty': line['quantity'],
                    'price_unit': line['price_unit'],
                })
                for line in order_line
            ]
        })

        return {"success": True, "sale_order_id": sale_order.id}
