# -*- coding: utf-8 -*-
# from odoo import http


# class SecurityView(http.Controller):
#     @http.route('/security_view/security_view', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/security_view/security_view/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('security_view.listing', {
#             'root': '/security_view/security_view',
#             'objects': http.request.env['security_view.security_view'].search([]),
#         })

#     @http.route('/security_view/security_view/objects/<model("security_view.security_view"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('security_view.object', {
#             'object': obj
#         })

