# -*- coding: utf-8 -*-
# from odoo import http


# class AngkotLeave(http.Controller):
#     @http.route('/angkot_leave/angkot_leave', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/angkot_leave/angkot_leave/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('angkot_leave.listing', {
#             'root': '/angkot_leave/angkot_leave',
#             'objects': http.request.env['angkot_leave.angkot_leave'].search([]),
#         })

#     @http.route('/angkot_leave/angkot_leave/objects/<model("angkot_leave.angkot_leave"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('angkot_leave.object', {
#             'object': obj
#         })

