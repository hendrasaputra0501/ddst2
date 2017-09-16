# -*- coding: utf-8 -*-
from odoo import http

# class BeacukaiStockCustom(http.Controller):
#     @http.route('/beacukai_stock_custom/beacukai_stock_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/beacukai_stock_custom/beacukai_stock_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('beacukai_stock_custom.listing', {
#             'root': '/beacukai_stock_custom/beacukai_stock_custom',
#             'objects': http.request.env['beacukai_stock_custom.beacukai_stock_custom'].search([]),
#         })

#     @http.route('/beacukai_stock_custom/beacukai_stock_custom/objects/<model("beacukai_stock_custom.beacukai_stock_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('beacukai_stock_custom.object', {
#             'object': obj
#         })