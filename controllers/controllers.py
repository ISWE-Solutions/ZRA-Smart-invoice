# -*- coding: utf-8 -*-
# from odoo import http


# class ZraSmartInvoice(http.Controller):
#     @http.route('/zra_smart_invoice/zra_smart_invoice', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zra_smart_invoice/zra_smart_invoice/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zra_smart_invoice.listing', {
#             'root': '/zra_smart_invoice/zra_smart_invoice',
#             'objects': http.request.env['zra_smart_invoice.zra_smart_invoice'].search([]),
#         })

#     @http.route('/zra_smart_invoice/zra_smart_invoice/objects/<model("zra_smart_invoice.zra_smart_invoice"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zra_smart_invoice.object', {
#             'object': obj
#         })

