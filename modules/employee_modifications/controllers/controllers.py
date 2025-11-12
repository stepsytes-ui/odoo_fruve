# -*- coding: utf-8 -*-
# from odoo import http


# class EmployeeModifications(http.Controller):
#     @http.route('/employee_modifications/employee_modifications', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_modifications/employee_modifications/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_modifications.listing', {
#             'root': '/employee_modifications/employee_modifications',
#             'objects': http.request.env['employee_modifications.employee_modifications'].search([]),
#         })

#     @http.route('/employee_modifications/employee_modifications/objects/<model("employee_modifications.employee_modifications"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_modifications.object', {
#             'object': obj
#         })

