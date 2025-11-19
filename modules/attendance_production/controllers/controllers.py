# -*- coding: utf-8 -*-
# from odoo import http


# class AttendanceProduction(http.Controller):
#     @http.route('/attendance_production/attendance_production', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/attendance_production/attendance_production/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('attendance_production.listing', {
#             'root': '/attendance_production/attendance_production',
#             'objects': http.request.env['attendance_production.attendance_production'].search([]),
#         })

#     @http.route('/attendance_production/attendance_production/objects/<model("attendance_production.attendance_production"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('attendance_production.object', {
#             'object': obj
#         })

