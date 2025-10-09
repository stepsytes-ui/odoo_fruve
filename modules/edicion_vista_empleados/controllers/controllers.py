# -*- coding: utf-8 -*-
# from odoo import http


# class EdicionVistaEmpleados(http.Controller):
#     @http.route('/edicion_vista_empleados/edicion_vista_empleados', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/edicion_vista_empleados/edicion_vista_empleados/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('edicion_vista_empleados.listing', {
#             'root': '/edicion_vista_empleados/edicion_vista_empleados',
#             'objects': http.request.env['edicion_vista_empleados.edicion_vista_empleados'].search([]),
#         })

#     @http.route('/edicion_vista_empleados/edicion_vista_empleados/objects/<model("edicion_vista_empleados.edicion_vista_empleados"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('edicion_vista_empleados.object', {
#             'object': obj
#         })

