# -*- coding: utf-8 -*-
from odoo import http

# class MasterDataCustom(http.Controller):
#     @http.route('/master_data_custom/master_data_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/master_data_custom/master_data_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('master_data_custom.listing', {
#             'root': '/master_data_custom/master_data_custom',
#             'objects': http.request.env['master_data_custom.master_data_custom'].search([]),
#         })

#     @http.route('/master_data_custom/master_data_custom/objects/<model("master_data_custom.master_data_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('master_data_custom.object', {
#             'object': obj
#         })