# -*- coding: utf-8 -*-
# from odoo import http


# class ZktecoRealtimeConnector(http.Controller):
#     @http.route('/zkteco_realtime_connector/zkteco_realtime_connector', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zkteco_realtime_connector/zkteco_realtime_connector/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zkteco_realtime_connector.listing', {
#             'root': '/zkteco_realtime_connector/zkteco_realtime_connector',
#             'objects': http.request.env['zkteco_realtime_connector.zkteco_realtime_connector'].search([]),
#         })

#     @http.route('/zkteco_realtime_connector/zkteco_realtime_connector/objects/<model("zkteco_realtime_connector.zkteco_realtime_connector"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zkteco_realtime_connector.object', {
#             'object': obj
#         })

