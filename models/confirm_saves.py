from odoo import models, fields, api
import requests
import logging
from datetime import datetime
import json
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_type = fields.Char('Sale Type Code', default='N')
    receipt_type = fields.Char('Receipt Type Code', default='S')
    payment_type = fields.Char('Payment Type Code', default='01')
    sales_status = fields.Char('Sales Status Code', default='02')
    tpin = fields.Char(string='TPIN', size=10)
    export_country_id = fields.Many2one('res.country', string='Export Country')
    lpo = fields.Char(string='LPO')
    currency_id = fields.Many2one('res.currency', string='Currency')

    rcpt_no = fields.Integer(string='Receipt No')
    intrl_data = fields.Char(string='Internal Data')
    rcpt_sign = fields.Char(string='Receipt Sign')
    vsdc_rcpt_pbct_date = fields.Char(string='VSDC Receipt Publish Date')
    sdc_id = fields.Char(string='SDC ID')
    mrc_no = fields.Char(string='MRC No')
    qr_code_url = fields.Char(string='QR Code URL')

    def get_primary_tax(self, partner):
        if partner.tax_id:
            return partner.tax_id[0]
        else:
            move_lines = self.env['account.move.line'].search([('move_id', '=', self.id)])
            for line in move_lines:
                if line.tax_ids:
                    return line.tax_ids[0]
        return None

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

        if to_currency == self.env.company.currency_id:
            return rate.rate

        to_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', to_currency.id),
            ('name', '<=', fields.Date.today())
        ], order='name desc', limit=1)

        if not to_rate:
            raise ValidationError(f"No exchange rate found for {to_currency.name}.")

        return rate.rate / to_rate.rate

    def get_tax_rate(self, tax):
        return tax.amount if tax else 0.0

    def get_tax_description(self, tax):
        return tax.description if tax else ''

    def calculate_custom_subtotal(self):
        custom_subtotal = 0.0
        for line in self.invoice_line_ids:
            custom_subtotal += line.quantity * line.price_unit
        return custom_subtotal

    def calculate_taxable_amount(self, lines, tax_category):
        filtered_lines = [line for line in lines if
                          self.get_tax_description(self.get_primary_tax(self.partner_id)) == tax_category]
        return round(sum(line.price_subtotal for line in filtered_lines), 2)

    def calculate_tax_amount(self, lines, tax_category):
        filtered_lines = [line for line in lines if
                          self.get_tax_description(self.get_primary_tax(self.partner_id)) == tax_category]
        return round(sum(line.price_total - line.price_subtotal for line in filtered_lines), 2)

    def calculate_tax_inclusive_price(self, line):
        taxes = line.tax_ids.compute_all(line.price_unit, quantity=1, product=line.product_id, partner=self.partner_id)
        tax_inclusive_price = taxes['total_included']
        return tax_inclusive_price

    def get_sales_order_fields(self):
        """Retrieve tpin, lpo, and export_country_id from related sale order."""
        sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
        return sale_order.tpin, sale_order.lpo, sale_order.export_country_id.code if sale_order.export_country_id else None

    def action_post(self):
        _logger.info("Starting action_post method.")
        res = super(AccountMove, self).action_post()

        current_user = self.env.user
        subtotal_before_tax = self.calculate_custom_subtotal()

        tpin, lpo, export_country_code = self.get_sales_order_fields()

        exchange_rate = self.get_exchange_rate(self.currency_id, self.env.company.currency_id)

        api_url = "http://localhost:8085/trnsSales/saveSales"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "orgInvcNo": 0,
            "cisInvcNo": self.name,
            "custTin": tpin or "1999999999",
            "custNm": self.partner_id.name,
            "salesTyCd": self.sale_type or 'N',
            "rcptTyCd": self.receipt_type or 'S',
            "pmtTyCd": self.payment_type or '01',
            "salesSttsCd": self.sales_status or '02',
            "cfmDt": self.invoice_date.strftime('%Y%m%d%H%M%S') if self.invoice_date else None,
            "salesDt": datetime.now().strftime('%Y%m%d'),
            "stockRlsDt": None,
            "cnclReqDt": None,
            "cnclDt": None,
            "rfdDt": None,
            "rfdRsnCd": "",
            "totItemCnt": len(self.invoice_line_ids),
            "taxblAmtA": self.calculate_taxable_amount(self.invoice_line_ids, 'A'),
            "taxblAmtB": self.calculate_taxable_amount(self.invoice_line_ids, 'B'),
            "taxblAmtC": self.calculate_taxable_amount(self.invoice_line_ids, 'C'),
            "taxblAmtC1": self.calculate_taxable_amount(self.invoice_line_ids, 'C1'),
            "taxblAmtC2": self.calculate_taxable_amount(self.invoice_line_ids, 'C2'),
            "taxblAmtC3": self.calculate_taxable_amount(self.invoice_line_ids, 'C3'),
            "taxblAmtD": self.calculate_taxable_amount(self.invoice_line_ids, 'D'),
            "taxblAmtRvat": self.calculate_taxable_amount(self.invoice_line_ids, 'Rvat'),
            "taxblAmtE": self.calculate_taxable_amount(self.invoice_line_ids, 'E'),
            "taxblAmtF": self.calculate_taxable_amount(self.invoice_line_ids, 'F'),
            "taxblAmtIpl1": self.calculate_taxable_amount(self.invoice_line_ids, 'Ipl1'),
            "taxblAmtIpl2": self.calculate_taxable_amount(self.invoice_line_ids, 'Ipl2'),
            "taxblAmtTl": self.calculate_taxable_amount(self.invoice_line_ids, 'Tl'),
            "taxblAmtEcm": self.calculate_taxable_amount(self.invoice_line_ids, 'Ecm'),
            "taxblAmtExeeg": self.calculate_taxable_amount(self.invoice_line_ids, 'Exeeg'),
            "taxblAmtTot": self.calculate_taxable_amount(self.invoice_line_ids, 'Tot'),
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
            "taxAmtA": self.calculate_tax_amount(self.invoice_line_ids, 'A'),
            "taxAmtB": self.calculate_tax_amount(self.invoice_line_ids, 'B'),
            "taxAmtC": self.calculate_tax_amount(self.invoice_line_ids, 'C'),
            "taxAmtC1": self.calculate_tax_amount(self.invoice_line_ids, 'C1'),
            "taxAmtC2": self.calculate_tax_amount(self.invoice_line_ids, 'C2'),
            "taxAmtC3": self.calculate_tax_amount(self.invoice_line_ids, 'C3'),
            "taxAmtD": self.calculate_tax_amount(self.invoice_line_ids, 'D'),
            "taxAmtRvat": self.calculate_tax_amount(self.invoice_line_ids, 'Rvat'),
            "taxAmtE": self.calculate_tax_amount(self.invoice_line_ids, 'E'),
            "taxAmtF": self.calculate_tax_amount(self.invoice_line_ids, 'F'),
            "taxAmtIpl1": self.calculate_tax_amount(self.invoice_line_ids, 'Ipl1'),
            "taxAmtIpl2": self.calculate_tax_amount(self.invoice_line_ids, 'Ipl2'),
            "taxAmtTl": self.calculate_tax_amount(self.invoice_line_ids, 'Tl'),
            "taxAmtEcm": self.calculate_tax_amount(self.invoice_line_ids, 'Ecm'),
            "taxAmtExeeg": self.calculate_tax_amount(self.invoice_line_ids, 'Exeeg'),
            "taxAmtTot": self.calculate_tax_amount(self.invoice_line_ids, 'Tot'),
            "totTaxblAmt": round(sum(line.price_subtotal for line in self.invoice_line_ids), 2),
            "totTaxAmt": round(sum(line.price_total - line.price_subtotal for line in self.invoice_line_ids), 2),
            "totAmt": round(sum(line.price_total for line in self.invoice_line_ids), 2),
            "prchrAcptcYn": "Y",
            "remark": "sales",
            "regrId": current_user.id,
            "regrNm": current_user.name,
            "modrId": current_user.id,
            "modrNm": current_user.name,
            "saleCtyCd": "1",
            "lpoNumber": lpo or None,
            "currencyTyCd": self.currency_id.name if self.currency_id else "ZMW",
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
                    "prc": round(self.calculate_tax_inclusive_price(line), 2),
                    "splyAmt": round(line.quantity * self.calculate_tax_inclusive_price(line), 2),
                    "dcRt": line.discount,
                    "dcAmt": round(line.discount, 2),
                    "isrccCd": "",
                    "isrccNm": "",
                    "isrcRt": 0.0,
                    "isrcAmt": 0.0,
                    "vatCatCd": "A",
                    "exciseTxCatCd": None,
                    "vatTaxblAmt": line.quantity * line.product_id.list_price,
                    "exciseTaxblAmt": 0.0,
                    "vatAmt": round(line.price_total - line.price_subtotal, 2),
                    "exciseTxAmt": 0.0,
                    "totAmt": round((line.quantity * line.product_id.list_price) + round(
                        line.price_total - line.price_subtotal, 2), 2),
                }
                for index, line in enumerate(self.invoice_line_ids)
            ]
        }

        self._post_to_api(api_url, payload, "Save Sales API Response resultMsg")

        # Additional payloads for stock items and stock master
        payload_stock_items = {
            "tpin": "1018798746",
            "bhfId": "000",
            "sarNo": 1,
            "orgSarNo": 0,
            "regTyCd": "M",
            "custTpin": tpin or "1999999999",
            "custNm": self.partner_id.name,
            "custBhfId": "000",
            "sarTyCd": "11",
            "ocrnDt": self.invoice_date.strftime('%Y%m%d') if self.invoice_date else None,
            "totItemCnt": len(self.invoice_line_ids),
            "totTaxblAmt": round(sum(line.price_subtotal for line in self.invoice_line_ids), 2),
            "totTaxAmt": round(sum(line.price_total - line.price_subtotal for line in self.invoice_line_ids), 2),
            "totAmt": round(sum(line.price_total for line in self.invoice_line_ids), 2),
            "remark": 'Sales',
            "regrId": current_user.name,
            "regrNm": current_user.id,
            "modrNm": current_user.name,
            "modrId": current_user.id,
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
                    "itemExprDt": None,
                    "prc": round(line.price_unit, 2),
                    "splyAmt": round(line.price_subtotal, 2),
                    "totDcAmt": 0,
                    "vatCatCd": "A",
                    "exciseTxCatCd": "EXEEG",
                    "vatAmt": round(line.price_total - line.price_subtotal, 2),
                    "taxblAmt": 0,
                    "iplAmt": 0,
                    "tlAmt": 0,
                    "exciseTxAmt": 0,
                    "taxAmt": round(line.price_total - line.price_subtotal, 2),
                    "totAmt": round((line.quantity * line.product_id.list_price) + round(
                        line.price_total - line.price_subtotal, 2), 2),
                } for index, line in enumerate(self.invoice_line_ids)
            ]
        }

        self._post_to_stock_api('http://localhost:8085/stock/saveStockItems', payload_stock_items,
                                "Save Stock Item API Response Endpoint")

        for line in self.invoice_line_ids:
            # Fetch the available quantity from the stock quant model
            available_quants = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id.usage', '=', 'internal')
            ])
            available_qty = sum(quant.quantity for quant in available_quants)

            remaining_qty = available_qty - line.quantity

        payload_stock_master = {
            "tpin": "1018798746",
            "bhfId": "000",
            "regrId": current_user.name,
            "regrNm": current_user.id,
            "modrNm": current_user.name,
            "modrId": current_user.id,
            "stockItemList": [
                {
                    "itemCd": line.product_id.item_Cd,
                    "rsdQty": remaining_qty
                } for line in self.invoice_line_ids
            ]
        }
        self._post_to_stock_api('http://localhost:8085/stockMaster/saveStockMaster', payload_stock_master,
                                "Stock Master Endpoint response")

        return res

    def _post_to_api(self, url, payload, success_message_prefix):
        print('Payload being sent:', json.dumps(payload, indent=4))
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            result_msg = response_data.get('resultMsg', 'No result message returned')
            data = response_data.get('data')

            if data:
                rcpt_no = data.get('rcptNo')
                intrl_data = data.get('intrlData')
                rcpt_sign = data.get('rcptSign')
                vsdc_rcpt_pbct_date = data.get('vsdcRcptPbctDate')
                sdc_id = data.get('sdcId')
                mrc_no = data.get('mrcNo')
                qr_code_url = data.get('qrCodeUrl')

                # Log the response data
                print(f'Response Data - rcpt_no: {rcpt_no}, intrl_data: {intrl_data}, rcpt_sign: {rcpt_sign}, '
                      f'vsdc_rcpt_pbct_date: {vsdc_rcpt_pbct_date}, sdc_id: {sdc_id}, mrc_no: {mrc_no}, '
                      f'qr_code_url: {qr_code_url}')

                if self:
                    record = self[0]
                    record.message_post(body=f"{success_message_prefix}: {result_msg}")
                    _logger.info(f'{success_message_prefix}: {result_msg}')
                    print(f'{success_message_prefix}: {result_msg}')

                    record.write({
                        'rcpt_no': rcpt_no,
                        'intrl_data': intrl_data,
                        'rcpt_sign': rcpt_sign,
                        'vsdc_rcpt_pbct_date': vsdc_rcpt_pbct_date,
                        'sdc_id': sdc_id,
                        'mrc_no': mrc_no,
                        'qr_code_url': qr_code_url
                    })
                else:
                    _logger.warning('No records to post messages to')
                    print('No records to post messages to')

            else:
                _logger.error('No data returned in the response')
                print('No data returned in the response')

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if self:
                record = self[0]
                record.message_post(body=f"Error during API call: {error_msg}")
                _logger.error(f'API request failed: {error_msg}')
                print(f'API request failed: {error_msg}')
            else:
                _logger.error(f'API request failed: {error_msg} (No records to post messages to)')

    def _post_to_stock_api(self, url, payload, success_message_prefix):

        print('Payload being sent:', json.dumps(payload, indent=4))
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result_msg = response.json().get('resultMsg', 'No result message returned')
            if not self:
                _logger.warning('No records to post messages to')
                return
            for record in self:
                record.message_post(body=f"{success_message_prefix}: {result_msg}")
                _logger.info(f'{success_message_prefix}: {result_msg}')
                print(f'{success_message_prefix}: {result_msg}')
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if not self:
                _logger.error(f'API request failed: {error_msg} (No records to post messages to)')
                return
            for record in self:
                record.message_post(body=f"Error during API call: {error_msg}")
                _logger.error(f'API request failed: {error_msg}')
                print(f'API request failed: {error_msg}')
