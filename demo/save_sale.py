# from odoo import models, fields, api
# import requests
#
#
# class AccountPaymentRegister(models.TransientModel):
#     _inherit = 'account.payment.register'
#
#     def action_create_payments(self):
#         res = super(AccountPaymentRegister, self).action_create_payments()
#
#         # Create an instance of the new model to post in the chatter
#         try:
#             chatter_post = self.env['account.payment.register.chatter'].sudo().create({})
#             print(f"Chatter Post Created: {chatter_post.id}")
#             chatter_post.sudo().post_chatter_message()
#         except Exception as e:
#             print(f"Error during chatter post creation or message posting: {e}")
#
#         # Post to external API
#         api_url = "http://localhost:8085/trnsSales/saveSales"
#         payload = {
#
#             "tpin": "1018798746",
#             "bhfId": "000",
#             "orgInvcNo": 99,
#             "cisInvcNo": "SAP000011",
#             "custTin": "0782229123",
#             "custNm": "Test Customer",
#             "salesTyCd": "N",
#             "rcptTyCd": "R",
#             "pmtTyCd": "01",
#             "salesSttsCd": "02",
#             "cfmDt": "20240502102010",
#             "salesDt": "20240502",
#             "stockRlsDt": None,
#             "cnclReqDt": None,
#             "cnclDt": None,
#             "rfdDt": None,
#             "rfdRsnCd": "01",
#             "totItemCnt": 1,
#             "taxblAmtA": 86.2069,
#             "taxblAmtB": 0.0,
#             "taxblAmtC": 0.0,
#             "taxblAmtC1": 0.0,
#             "taxblAmtC2": 0.0,
#             "taxblAmtC3": 0.0,
#             "taxblAmtD": 0.0,
#             "taxblAmtRvat": 0.0,
#             "taxblAmtE": 0.0,
#             "taxblAmtF": 0.0,
#             "taxblAmtIpl1": 0,
#             "taxblAmtIpl2": 0.0,
#             "taxblAmtTl": 0,
#             "taxblAmtEcm": 0,
#             "taxblAmtExeeg": 0.0,
#             "taxblAmtTot": 0.0,
#             "taxRtA": 16,
#             "taxRtB": 16,
#             "taxRtC1": 0,
#             "taxRtC2": 0,
#             "taxRtC3": 0,
#             "taxRtD": 0,
#             "taxRtRvat": 16,
#             "taxRtE": 0,
#             "taxRtF": 10,
#             "taxRtIpl1": 5,
#             "taxRtIpl2": 0,
#             "taxRtTl": 1.5,
#             "taxRtEcm": 5,
#             "taxRtExeeg": 3,
#             "taxRtTot": 0,
#             "taxAmtA": 13.7931,
#             "taxAmtB": 0.0,
#             "taxAmtC": 0.0,
#             "taxAmtC1": 0.0,
#             "taxAmtC2": 0.0,
#             "taxAmtC3": 0.0,
#             "taxAmtD": 0.0,
#             "taxAmtRvat": 0.0,
#             "taxAmtE": 0.0,
#             "taxAmtF": 0,
#             "taxAmtIpl1": 0,
#             "taxAmtIpl2": 0.0,
#             "taxAmtTl": 0,
#             "taxAmtEcm": 0.0,
#             "taxAmtExeeg": 0.0,
#             "taxAmtTot": 0.0,
#             "totTaxblAmt": 86.2069,
#             "totTaxAmt": 13.7931,
#             "totAmt": 100,
#             "prchrAcptcYn": "N",
#             "remark": "",
#             "regrId": "admin",
#             "regrNm": "admin",
#             "modrId": "admin",
#             "modrNm": "admin",
#             "saleCtyCd": "1",
#             "lpoNumber": "ZM2379729723",
#             "currencyTyCd": "ZMW",
#             "exchangeRt": "1",
#             "destnCountryCd": "",
#             "dbtRsnCd": "",
#             "invcAdjustReason": "",
#             "itemList": [
#                 {
#                     "itemSeq": 1,
#                     "itemCd": "20044",
#                     "itemClsCd": "50102517",
#                     "itemNm": "Chicken Wings",
#                     "bcd": "",
#                     "pkgUnitCd": "BA",
#                     "pkg": 0.0,
#                     "qtyUnitCd": "BE",
#                     "qty": 1.0,
#                     "prc": 100.0,
#                     "splyAmt": 100.0,
#                     "dcRt": 0.0,
#                     "dcAmt": 0.0,
#                     "isrccCd": "",
#                     "isrccNm": "",
#                     "isrcRt": 0.0,
#                     "isrcAmt": 0.0,
#                     "vatCatCd": "A",
#                     "exciseTxCatCd": None,
#                     "vatTaxblAmt": 86.2069,
#                     "exciseTaxblAmt": 0,
#                     "vatAmt": 13.7931,
#                     "exciseTxAmt": 0,
#                     "totAmt": 100
#                 }
#             ]
#
#         }
#         try:
#             response = requests.post(api_url, json=payload)
#             response_data = response.json()
#             result_msg = response_data.get("resultMsg", "No resultMsg in response")
#             print(f"API Response resultMsg: {result_msg}")
#         except Exception as e:
#             print(f"Error during API call: {e}")
#
#         return res
#
#
# class AccountPaymentRegisterChatter(models.Model):
#     _name = 'account.payment.register.chatter'
#     _description = 'Payment Register Chatter'
#     _inherit = 'mail.thread'
#
#     # Add any additional fields you might need for this model
#     name = fields.Char(string='Name')
#
#     def post_chatter_message(self):
#         try:
#             print(f"Attempting to post chatter message for record: {self.id}")
#             self.message_post(body="Payment has been registered.")
#             print('Message posted successfully')
#         except Exception as e:
#             print(f"Error posting chatter message: {e}")
