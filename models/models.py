# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class zra_smart_invoice(models.Model):
#     _name = 'zra_smart_invoice.zra_smart_invoice'
#     _description = 'zra_smart_invoice.zra_smart_invoice'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

