# -*- coding: utf-8 -*-
# from odoo import http


# class Maintenance(http.Controller):
#     @http.route('/maintenance/maintenance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maintenance/maintenance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('maintenance.listing', {
#             'root': '/maintenance/maintenance',
#             'objects': http.request.env['maintenance.maintenance'].search([]),
#         })

#     @http.route('/maintenance/maintenance/objects/<model("maintenance.maintenance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maintenance.object', {
#             'object': obj
#         })

