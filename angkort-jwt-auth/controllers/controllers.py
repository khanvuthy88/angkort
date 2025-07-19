# -*- coding: utf-8 -*-
# from odoo import http


# class Angkort-jwt-auth(http.Controller):
#     @http.route('/angkort-jwt-auth/angkort-jwt-auth', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/angkort-jwt-auth/angkort-jwt-auth/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('angkort-jwt-auth.listing', {
#             'root': '/angkort-jwt-auth/angkort-jwt-auth',
#             'objects': http.request.env['angkort-jwt-auth.angkort-jwt-auth'].search([]),
#         })

#     @http.route('/angkort-jwt-auth/angkort-jwt-auth/objects/<model("angkort-jwt-auth.angkort-jwt-auth"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('angkort-jwt-auth.object', {
#             'object': obj
#         })

