# -*- coding: utf-8 -*-
# from odoo import http


# class Customers(http.Controller):
#     @http.route('/customers/customers', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/customers/customers/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('customers.listing', {
#             'root': '/customers/customers',
#             'objects': http.request.env['customers.customers'].search([]),
#         })

#     @http.route('/customers/customers/objects/<model("customers.customers"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('customers.object', {
#             'object': obj
#         })

