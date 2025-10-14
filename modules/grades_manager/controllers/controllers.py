# -*- coding: utf-8 -*-
# from odoo import http


# class GradesManager(http.Controller):
#     @http.route('/grades_manager/grades_manager', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/grades_manager/grades_manager/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('grades_manager.listing', {
#             'root': '/grades_manager/grades_manager',
#             'objects': http.request.env['grades_manager.grades_manager'].search([]),
#         })

#     @http.route('/grades_manager/grades_manager/objects/<model("grades_manager.grades_manager"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('grades_manager.object', {
#             'object': obj
#         })

