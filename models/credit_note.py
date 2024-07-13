from odoo import models, fields, api
import requests
import logging
from datetime import datetime
import json
import re
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'


    reason = fields.Selection([
        ('01', 'Missing Quantity'),
        ('02', 'Missing Item'),
        ('03', 'Damaged'),
        ('04', 'Wasted'),
        ('05', 'Raw Material Shortage'),
        ('06', 'Refund'),
        ('07', 'Wrong Customer TPIN'),
        ('08', 'Wrong Customer name'),
        ('09', 'Wrong Amount/price'),
        ('10', 'Wrong Quantity'),
        ('11', 'Wrong Item(s)'),
        ('12', 'Wrong tax type'),
        ('13', 'Other reason'),
    ], string='Reason', required=True)

    def get_primary_tax(self, partner):
        if partner.tax_id:
            return partner.tax_id[0]
        else:
            credit_move_id = self._context.get('active_id')
            credit_move = self.env['account.move'].browse(credit_move_id)
            move_lines = self.env['account.move.line'].search([('move_id', '=', credit_move.id)])
            for line in move_lines:
                if line.tax_ids:
                    return line.tax_ids[0]
        return None

    def get_tax_description(self, tax):
        return tax.description if tax else ''

    def my_custom_method(self):
        credit_move = self.env['account.move'].browse(self._context.get('active_id'))
        partner = credit_move.partner_id

    def get_exchange_rate(self, from_currency, to_currency):
        """Retrieve the latest exchange rate between two currencies."""
        if from_currency == to_currency:
            return 1.0

        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', from_currency.id),
            ('name', '<=', fields.Date.today())
        ], order='name desc', limit=1)

        if not rate:
            raise ValidationError(f"No exchange rate found for {from_currency.name} to {to_currency.name}.")

        # Assuming ZMW is the company currency, we need to get the inverse rate if needed.
        if to_currency == self.env.company.currency_id:
            return rate.rate

        # If the to_currency is not the company currency, calculate the rate to the company currency and then to the target currency.
        to_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', to_currency.id),
            ('name', '<=', fields.Date.today())
        ], order='name desc', limit=1)

        if not to_rate:
            raise ValidationError(f"No exchange rate found for {to_currency.name}.")

        return rate.rate / to_rate.rate

    def get_tax_rate(self, tax):
        return tax.amount if tax else 0.0

    def calculate_taxable_amount(self, lines, tax_category):
        filtered_lines = [line for line in lines if
                          self.get_tax_description(self.get_primary_tax(line.partner_id)) == tax_category]
        return round(sum(line.price_subtotal for line in filtered_lines), 2)

    def calculate_tax_amount(self, lines, tax_category):
        filtered_lines = [line for line in lines if
                          self.get_tax_description(self.get_primary_tax(line.partner_id)) == tax_category]
        return round(sum(line.price_total - line.price_subtotal for line in filtered_lines), 2)

    def calculate_tax_inclusive_price(self, line):
        taxes = line.tax_ids.compute_all(line.price_unit, quantity=1, product=line.product_id,
                                         partner=line.partner_id)
        tax_inclusive_price = taxes['total_included']
        return tax_inclusive_price

    def create_credit_note_payload(self):
        for move in self.move_ids:

            current_user = self.env.user

            tpin = move.partner_id.tpin if move.partner_id else None

            # Fetch the related sale order to get the LPO and export country code
            sale_order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            lpo = sale_order.lpo if sale_order else None
            export_country_code = sale_order.export_country_id.code if sale_order and sale_order.export_country_id else None

            exchange_rate = self.get_exchange_rate(move.currency_id, self.env.company.currency_id)

            match = re.search(r'/(\d+)$', move.name)

            if match:
                last_digits = match.group(1)
                invc_no = int(last_digits)
                # print(invc_no)  # Output: 117
            else:
                print("No digits found at the end of the string.")

            credit_move = self.env['account.move'].browse(self._context.get('active_id'))
            partner = credit_move.partner_id
            # print('move partner', partner)
            # print(self.get_tax_description(self.get_primary_tax(partner)))
            payload = {
                "tpin": "1018798746",
                "bhfId": "000",
                "orgSdcId": "SDC0010000647",
                "orgInvcNo": invc_no,
                "cisInvcNo": move.name,
                "custTin": tpin or '1999999999',
                "custNm": move.partner_id.name,
                "salesTyCd": "N",
                "rcptTyCd": "R",
                "pmtTyCd": "01",
                "salesSttsCd": "02",
                "cfmDt": move.invoice_date.strftime('%Y%m%d%H%M%S') if move.invoice_date else None,
                "salesDt": datetime.now().strftime('%Y%m%d'),
                "stockRlsDt": None,
                "cnclReqDt": None,
                "cnclDt": None,
                "rfdDt": None,
                "rfdRsnCd": self.reason,
                "totItemCnt": len(move.invoice_line_ids),
                "taxblAmtA": self.calculate_taxable_amount(move.invoice_line_ids, 'A'),
                "taxblAmtB": self.calculate_taxable_amount(move.invoice_line_ids, 'B'),
                "taxblAmtC": self.calculate_taxable_amount(move.invoice_line_ids, 'C'),
                "taxblAmtC1": self.calculate_taxable_amount(move.invoice_line_ids, 'C1'),
                "taxblAmtC2": self.calculate_taxable_amount(move.invoice_line_ids, 'C2'),
                "taxblAmtC3": self.calculate_taxable_amount(move.invoice_line_ids, 'C3'),
                "taxblAmtD": self.calculate_taxable_amount(move.invoice_line_ids, 'D'),
                "taxblAmtRvat": self.calculate_taxable_amount(move.invoice_line_ids, 'Rvat'),
                "taxblAmtE": self.calculate_taxable_amount(move.invoice_line_ids, 'E'),
                "taxblAmtF": self.calculate_taxable_amount(move.invoice_line_ids, 'F'),
                "taxblAmtIpl1": self.calculate_taxable_amount(move.invoice_line_ids, 'Ipl1'),
                "taxblAmtIpl2": self.calculate_taxable_amount(move.invoice_line_ids, 'Ipl2'),
                "taxblAmtTl": self.calculate_taxable_amount(move.invoice_line_ids, 'Tl'),
                "taxblAmtEcm": self.calculate_taxable_amount(move.invoice_line_ids, 'Ecm'),
                "taxblAmtExeeg": self.calculate_taxable_amount(move.invoice_line_ids, 'Exeeg'),
                "taxblAmtTot": self.calculate_taxable_amount(move.invoice_line_ids, 'Tot'),
                "taxRtA": 16,
                "taxRtB": 16,
                "taxRtC1": 0.0,
                "taxRtC2": 0.0,
                "taxRtC3": 0.0,
                "taxRtD": 0.0,
                "taxRtRvat": 16,
                "taxRtE": 0.0,
                "taxRtF": 10,
                "taxRtIpl1": 5,
                "taxRtIpl2": 0.0,
                "taxRtTl": 1.5,
                "taxRtEcm": 5,
                "taxRtExeeg": 3,
                "taxRtTot": 0.0,
                "taxAmtA": self.calculate_tax_amount(move.invoice_line_ids, 'A'),
                "taxAmtB": self.calculate_tax_amount(move.invoice_line_ids, 'B'),
                "taxAmtC": self.calculate_tax_amount(move.invoice_line_ids, 'C'),
                "taxAmtC1": self.calculate_tax_amount(move.invoice_line_ids, 'C1'),
                "taxAmtC2": self.calculate_tax_amount(move.invoice_line_ids, 'C2'),
                "taxAmtC3": self.calculate_tax_amount(move.invoice_line_ids, 'C3'),
                "taxAmtD": self.calculate_tax_amount(move.invoice_line_ids, 'D'),
                "taxAmtRvat": self.calculate_tax_amount(move.invoice_line_ids, 'Rvat'),
                "taxAmtE": self.calculate_tax_amount(move.invoice_line_ids, 'E'),
                "taxAmtF": self.calculate_tax_amount(move.invoice_line_ids, 'F'),
                "taxAmtIpl1": self.calculate_tax_amount(move.invoice_line_ids, 'Ipl1'),
                "taxAmtIpl2": self.calculate_tax_amount(move.invoice_line_ids, 'Ipl2'),
                "taxAmtTl": self.calculate_tax_amount(move.invoice_line_ids, 'Tl'),
                "taxAmtEcm": self.calculate_tax_amount(move.invoice_line_ids, 'Ecm'),
                "taxAmtExeeg": self.calculate_tax_amount(move.invoice_line_ids, 'Exeeg'),
                "taxAmtTot": self.calculate_tax_amount(move.invoice_line_ids, 'Tot'),
                "totTaxblAmt": round(sum(line.price_subtotal for line in move.invoice_line_ids), 2),
                "totTaxAmt": round(sum(line.price_total - line.price_subtotal for line in move.invoice_line_ids), 2),
                "totAmt": round(sum(line.price_total for line in move.invoice_line_ids), 2),
                "prchrAcptcYn": "N",
                "remark": "credit note",
                "regrId": current_user.id,
                "regrNm": current_user.name,
                "modrId": current_user.id,
                "modrNm": current_user.name,
                "saleCtyCd": "1",
                "lpoNumber": lpo or None,
                "currencyTyCd": move.currency_id.name if move.currency_id else "ZMW",
                "exchangeRt": str(exchange_rate),
                "destnCountryCd": export_country_code or "ZM",
                "dbtRsnCd": "",
                "invcAdjustReason": "",
                "itemList": [
                    {
                        "itemSeq": index + 1,
                        "itemCd": line.product_id.item_Cd,
                        "itemClsCd": line.product_id.item_cls_cd,
                        "itemNm": line.product_id.name,
                        "bcd": line.product_id.barcode,
                        "pkgUnitCd": line.product_id.packaging_unit_cd,  # Example static value, can be dynamic
                        "pkg": line.quantity,
                        "qtyUnitCd": line.product_id.quantity_unit_cd,
                        "qty": line.quantity,
                        "prc": self.calculate_tax_inclusive_price(line),
                        "splyAmt": line.quantity * self.calculate_tax_inclusive_price(line),
                        "dcRt": line.discount,
                        "dcAmt": round(line.discount, 2),
                        "isrccCd": "",
                        "isrccNm": "",
                        "isrcRt": 0.0,
                        "isrcAmt": 0.0,
                        "vatCatCd": self.get_tax_description(self.get_primary_tax(partner)),
                        "exciseTxCatCd": None,
                        "vatTaxblAmt": line.quantity * line.product_id.list_price,
                        "exciseTaxblAmt": 0.0,
                        "vatAmt": round(line.price_total - line.price_subtotal, 2),
                        "exciseTxAmt": 0.0,
                        "totAmt": (line.quantity * line.product_id.list_price) + round(
                            line.price_total - line.price_subtotal, 2),
                    } for index, line in enumerate(move.invoice_line_ids)
                ]
            }

            print('Payload being sent:', json.dumps(payload, indent=4))

            # Print the payload for debugging
            _logger.info("Credit Note Payload: %s", payload)

            return payload

    def create_credit_note_api_call(self):
        api_url = "http://localhost:8085/trnsSales/saveSales"
        payload = self.create_credit_note_payload()
        return self._post_to_api(api_url, payload, "API Response Credit Note")

    def refund_moves(self):
        res = super(AccountMoveReversal, self).refund_moves()
        self._process_moves()
        return res

    def modify_moves(self):
        res = super(AccountMoveReversal, self).modify_moves()
        self._process_moves()
        return res

    def _process_moves(self):
        for move in self.move_ids:
            # Process credit note API call
            result_msg = self.create_credit_note_api_call()
            move.message_post(body=f"API Response Credit Note resultMsg: {result_msg}")

            current_user = self.env.user
            invoice_line_ids = move.invoice_line_ids

            credit_move = self.env['account.move'].browse(self._context.get('active_id'))
            partner = credit_move.partner_id
            # Prepare the item list for the first endpoint
            item_list = [
                {
                    "itemSeq": index + 1,
                    "itemCd": line.product_id.item_Cd,
                    "itemClsCd": line.product_id.item_cls_cd,
                    "itemNm": line.product_id.name,
                    "bcd": line.product_id.barcode,
                    "pkgUnitCd": line.product_id.packaging_unit_cd,
                    "pkg": line.quantity,
                    "qtyUnitCd": line.product_id.quantity_unit_cd,
                    "qty": line.quantity,
                    "itemExprDt": None,
                    "prc": self.calculate_tax_inclusive_price(line),
                    "splyAmt": line.quantity * self.calculate_tax_inclusive_price(line),
                    "totDcAmt": 0,
                    "taxblAmt": line.price_subtotal,
                    "vatCatCd": self.get_tax_description(self.get_primary_tax(partner)),
                    "iplCatCd": "IPL1",
                    "tlCatCd": "TL",
                    "exciseTxCatCd": "EXEEG",
                    "vatAmt": round(line.price_total - line.price_subtotal, 2),
                    "iplAmt": 0.0,
                    "tlAmt": 0.0,
                    "exciseTxAmt": 0.0,
                    "taxAmt": round(line.price_total - line.price_subtotal, 2),
                    "totAmt": round(line.price_total, 2)
                } for index, line in enumerate(invoice_line_ids)
            ]

            # Prepare the payload for the first endpoint
            payload_new_endpoint = {
                "tpin": "1018798746",
                "bhfId": "000",
                "sarNo": 1,
                "orgSarNo": 0,
                "regTyCd": "M",
                "custTpin": move.partner_id.tpin or "1999999999",
                "custNm": move.partner_id.name if move.partner_id else None,
                "custBhfId": "000",
                "sarTyCd": "03",
                "ocrnDt": move.invoice_date.strftime('%Y%m%d') if move.invoice_date else None,
                "totItemCnt": len(invoice_line_ids),
                "totTaxblAmt": round(sum(line.price_subtotal for line in invoice_line_ids), 2),
                "totTaxAmt": round(sum(line.price_total - line.price_subtotal for line in invoice_line_ids), 2),
                "totAmt": round(sum(line.price_total for line in invoice_line_ids), 2),
                "remark": 'Credit Note',
                "regrId": current_user.id,
                "regrNm": current_user.name,
                "modrNm": current_user.name,
                "modrId": current_user.id,
                "itemList": item_list
            }

            # Send the payload for the first endpoint
            result_msg_new_endpoint = self._post_to_api('http://localhost:8085/stock/saveStockItems',
                                                        payload_new_endpoint, "Save Stock Item API Response")
            move.message_post(body=f"API Response New Endpoint: {result_msg_new_endpoint}")
            # print(f"Save Stock Item API Response: {result_msg_new_endpoint}")

            # Prepare the stock item list for the second endpoint
            stock_item_list = []
            for line in invoice_line_ids:
                product = line.product_id
                stock_item_list.append({
                    "itemCd": product.item_Cd,
                    "rsdQty": line.quantity
                })

            # Prepare the payload for the second endpoint
            payload_stock = {
                "tpin": "1018798746",
                "bhfId": "000",
                "regrId": current_user.id,
                "regrNm": current_user.name,
                "modrNm": current_user.name,
                "modrId": current_user.id,
                "stockItemList": stock_item_list
            }

            # Send the payload for the second endpoint
            result_msg_stock = self._post_to_api('http://localhost:8085/stockMaster/saveStockMaster', payload_stock,
                                                 "Save Stock Master Endpoint response:")
            move.message_post(body=f"Endpoint response: {result_msg_stock}")
            # print(f"Save Stock Master Endpoint response: {result_msg_stock}")

    def _post_to_api(self, url, payload, success_message_prefix):
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result_msg = response.json().get('resultMsg', 'No result message returned')
            _logger.info(f'{success_message_prefix}: {result_msg}')
            print(f'{success_message_prefix}: {result_msg}')
            return result_msg
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            _logger.error(f'API request failed: {error_msg}')
            print(f'API request failed: {error_msg}')
            return f"Error during API call: {error_msg}"


