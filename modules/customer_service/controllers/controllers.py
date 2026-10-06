# -*- coding: utf-8 -*-
# from odoo import http


# class CustomerService(http.Controller):
#     @http.route('/customer_service/customer_service', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/customer_service/customer_service/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('customer_service.listing', {
#             'root': '/customer_service/customer_service',
#             'objects': http.request.env['customer_service.customer_service'].search([]),
#         })

#     @http.route('/customer_service/customer_service/objects/<model("customer_service.customer_service"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('customer_service.object', {
#             'object': obj
#         })

