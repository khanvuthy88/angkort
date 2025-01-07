from odoo import http
from odoo.http import request

BASE_URL = '/angkort/api/v1'


class ProductController(http.Controller):

    @http.route(f"{BASE_URL}/product", auth="public", type="json", cors="*")
    def product(self):
        pass