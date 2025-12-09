# -*- coding: utf-8 -*-
# from odoo import http


# class Overtime(http.Controller):
#     @http.route('/overtime/overtime', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/overtime/overtime/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('overtime.listing', {
#             'root': '/overtime/overtime',
#             'objects': http.request.env['overtime.overtime'].search([]),
#         })

#     @http.route('/overtime/overtime/objects/<model("overtime.overtime"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('overtime.object', {
#             'object': obj
#         })

