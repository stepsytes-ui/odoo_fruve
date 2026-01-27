# -*- coding: utf-8 -*-
# from odoo import http


# class BirthdaysCalendary(http.Controller):
#     @http.route('/birthdays_calendary/birthdays_calendary', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/birthdays_calendary/birthdays_calendary/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('birthdays_calendary.listing', {
#             'root': '/birthdays_calendary/birthdays_calendary',
#             'objects': http.request.env['birthdays_calendary.birthdays_calendary'].search([]),
#         })

#     @http.route('/birthdays_calendary/birthdays_calendary/objects/<model("birthdays_calendary.birthdays_calendary"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('birthdays_calendary.object', {
#             'object': obj
#         })

