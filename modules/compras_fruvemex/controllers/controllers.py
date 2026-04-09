# -*- coding: utf-8 -*-
# from odoo import http


# class ComprasFruvemex(http.Controller):
#     @http.route('/compras_fruvemex/compras_fruvemex', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/compras_fruvemex/compras_fruvemex/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('compras_fruvemex.listing', {
#             'root': '/compras_fruvemex/compras_fruvemex',
#             'objects': http.request.env['compras_fruvemex.compras_fruvemex'].search([]),
#         })

#     @http.route('/compras_fruvemex/compras_fruvemex/objects/<model("compras_fruvemex.compras_fruvemex"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('compras_fruvemex.object', {
#             'object': obj
#         })

