# from odoo import models, fields, api, _
# import requests
# import logging
# import csv
#
# _logger = logging.getLogger(__name__)
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     classification = fields.Selection(
#         selection='_get_classification_options',
#         string='Item Classification',
#         required=True
#     )
#     item_cls_cd = fields.Char(string='Item Classification Code', compute='_compute_classification_data', store=True)
#     item_cls_lvl = fields.Integer(string='Item Classification Level', compute='_compute_classification_data', store=True)
#     tax_ty_cd = fields.Char(string='Tax Type Code', compute='_compute_classification_data', store=True)
#     mjr_tg_yn = fields.Char(string='Major Target', compute='_compute_classification_data', store=True)
#     use_yn = fields.Char(string='Use', compute='_compute_classification_data', store=True)
#
#     def _default_origin_country(self):
#         return self.env.ref('base.zm')
#
#     origin_country_id = fields.Many2one('res.country', string='Origin Country', default=_default_origin_country)
#     origin_country_cd = fields.Char(string='Origin Country Code', readonly=True)
#
#     @api.onchange('origin_country_id')
#     def _onchange_origin_country_id(self):
#         if self.origin_country_id:
#             self.origin_country_cd = self.origin_country_id.code
#         else:
#             self.origin_country_cd = ''
#
#     @api.model
#     def _get_classification_options(self):
#         classification_data = self.env['zra.item.save'].fetch_classification_data()
#         return [(item[0], item[0]) for item in classification_data]
#
#     @api.depends('classification')
#     def _compute_classification_data(self):
#         classification_data = {item[0]: item[1] for item in self.env['zra.item.save'].fetch_classification_data()}
#         for record in self:
#             selected_data = classification_data.get(record.classification)
#             if selected_data:
#                 record.item_cls_cd = selected_data['itemClsCd']
#                 record.use_yn = selected_data['useYn']
#             else:
#                 record.item_cls_cd = ''
#                 record.use_yn = ''
#
#     @api.model
#     def create(self, vals):
#         if 'origin_country_id' in vals:
#             country = self.env['res.country'].browse(vals['origin_country_id'])
#             vals['origin_country_cd'] = country.code
#         record = super(ProductTemplate, self).create(vals)
#         record._post_item_data(vals)
#         return record
#
#     def _post_item_data(self, vals):
#         current_user = self.env.user
#         origin_country_cd = vals.get('origin_country_cd', self.origin_country_cd)
#         _logger.debug('Posting item data with values: %s', vals)
#         url = 'http://localhost:8085/items/saveItem'
#         payload = {
#             "tpin": "1018798746",
#             "bhfId": "000",
#             "itemCd": "ZM2NTBA0000009",
#             "itemClsCd": self.item_cls_cd,
#             "itemTyCd": "2",
#             "itemNm": self.name,
#             "itemStdNm": self.name,
#             "orgnNatCd": origin_country_cd,
#             "pkgUnitCd": "NT",
#             "qtyUnitCd": "U",
#             "vatCatCd": "A",
#             "btchNo": None,
#             "bcd": None,
#             "dftPrc": self.list_price,
#             "addInfo": None,
#             "sftyQty": None,
#             "isrcAplcbYn": "N",
#             "useYn": self.use_yn,
#             "regrNm": current_user.name,
#             "regrId": current_user.id,
#             "modrNm": current_user.name,
#             "modrId": current_user.id
#         }
#         headers = {
#             'Content-Type': 'application/json'
#         }
#         # print(payload)
#         try:
#             response = requests.post(url, json=payload, headers=headers)
#             response.raise_for_status()
#             if response.status_code == 200:
#                 result_data = response.json()
#                 result_msg = result_data.get("resultMsg")
#                 _logger.debug('Success: %s', result_msg)
#                 self.message_post(body="API Response Item registered: %s, \nProduct Name: %s, Classification Code: %s" % (result_msg, self.name, self.item_cls_cd))
#                 return self.action_client_action(result_msg, 'success')
#             else:
#                 self._log_error(vals, response.text)
#                 self.message_post(body="API Error Response SaveItem: %s, \nProduct Name: %s, Classification Code: %s" % (response.text, self.name, self.item_cls_cd))
#                 return self.action_client_action(response.text, 'danger')
#         except requests.exceptions.RequestException as e:
#             _logger.error('Failed to save item: %s', e)
#             self._log_error(vals, str(e))
#             self.message_post(body="Exception occurred: %s\nProduct Name: %s, Classification Code: %s" % (str(e), self.name, self.item_cls_cd))
#             return self.action_client_action(str(e), 'danger')
#
#     def _log_error(self, vals, error_message):
#         log_file_path = '/var/log/odoo/zra_smart_invoice_error_log.csv'
#         with open(log_file_path, 'a', newline='') as csvfile:
#             writer = csv.writer(csvfile)
#             writer.writerow([vals.get("default_code", ""), error_message])
#
#     def action_client_action(self, message, message_type):
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Notification'),
#                 'type': message_type,
#                 'sticky': False
#             }
#         }
