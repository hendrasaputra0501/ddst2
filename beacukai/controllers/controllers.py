# -*- coding: utf-8 -*-
from odoo import http

# class Beacukai(http.Controller):
#     @http.route('/beacukai/beacukai/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/beacukai/beacukai/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('beacukai.listing', {
#             'root': '/beacukai/beacukai',
#             'objects': http.request.env['beacukai.beacukai'].search([]),
#         })

#     @http.route('/beacukai/beacukai/objects/<model("beacukai.beacukai"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('beacukai.object', {
#             'object': obj
#         })