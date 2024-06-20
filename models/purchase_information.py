from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class PurchaseData(models.Model):
    _name = 'purchase.data'
    _description = 'Purchase Data'

    spplr_tpin = fields.Char(string='Supplier TPIN')
    spplr_nm = fields.Char(string='Supplier Name')
    spplr_bhf_id = fields.Char(string='Supplier BHF ID')
    spplr_invc_no = fields.Integer(string='Invoice No')
    rcpt_ty_cd = fields.Char(string='Receipt Type Code')
    pmt_ty_cd = fields.Char(string='Payment Type Code')
    cfm_dt = fields.Datetime(string='Confirmation Date')
    sales_dt = fields.Date(string='Sales Date')
    stock_rls_dt = fields.Datetime(string='Stock Release Date')
    tot_item_cnt = fields.Integer(string='Total Item Count')
    tot_taxbl_amt = fields.Float(string='Total Taxable Amount')
    tot_tax_amt = fields.Float(string='Total Tax Amount')
    tot_amt = fields.Float(string='Total Amount')
    remark = fields.Text(string='Remark')
    item_list = fields.One2many('purchase.item', 'purchase_id', string='Item List')
    fetched = fields.Boolean(string="Fetched", default=False)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft')

    fetch_selection = fields.Selection(
        string='Select Data to Fetch',
        selection='_get_fetch_options'
    )

    @api.model
    def _get_fetch_options(self):
        url = "http://localhost:8085/trnsPurchase/selectTrnsPurchaseSales"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "lastReqDt": "20240105210300"
        }

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error('Error fetching fetch options: %s', e)
            raise UserError(_('Failed to get fetch options from the endpoint.'))

        try:
            result = response.json()
        except ValueError as e:
            _logger.error('Error parsing JSON response: %s', e)
            raise UserError(_('Failed to parse response from the endpoint.'))

        if result.get('resultCd') == '000':
            sale_list = result['data'].get('saleList', [])
            existing_invoices = self.search([]).mapped('spplr_invc_no')
            new_options = [(str(sale['spplrInvcNo']), f"{sale['spplrNm']} - {sale['spplrTpin']}") for sale in sale_list
                           if sale['spplrInvcNo'] and sale['spplrInvcNo'] not in existing_invoices]
            return new_options
        else:
            _logger.error('Failed to fetch data: %s', result.get('resultMsg'))
            raise UserError(_('Failed to fetch options: %s') % result.get('resultMsg'))

    def fetch_purchase_data(self):
        selected_option = self.fetch_selection
        if not selected_option:
            raise UserError(_('Please select an option to fetch data.'))

        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "lastReqDt": "20240105210300"
        }

        url = "http://localhost:8085/trnsPurchase/selectTrnsPurchaseSales"
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error('Error fetching purchase data: %s', e)
            raise UserError(_('Failed to fetch data from the endpoint.'))

        try:
            result = response.json()
        except ValueError as e:
            _logger.error('Error parsing JSON response: %s', e)
            raise UserError(_('Failed to parse response from the endpoint.'))

        if result.get('resultCd') == '000':
            selected_invoice_number = int(selected_option)
            for sale in result['data']['saleList']:
                if sale['spplrInvcNo'] == selected_invoice_number:
                    self.spplr_tpin = sale['spplrTpin']
                    self.spplr_nm = sale['spplrNm']
                    self.spplr_bhf_id = sale['spplrBhfId']
                    self.spplr_invc_no = sale['spplrInvcNo']
                    self.rcpt_ty_cd = sale['rcptTyCd']
                    self.pmt_ty_cd = sale['pmtTyCd']
                    self.cfm_dt = datetime.strptime(sale['cfmDt'], '%Y%m%d%H%M%S')
                    self.sales_dt = datetime.strptime(sale['salesDt'], '%Y%m%d').date()
                    self.stock_rls_dt = datetime.strptime(sale['stockRlsDt'], '%Y%m%d%H%M%S')
                    self.tot_item_cnt = sale['totItemCnt']
                    self.tot_taxbl_amt = sale['totTaxblAmt']
                    self.tot_tax_amt = sale['totTaxAmt']
                    self.tot_amt = sale['totAmt']
                    self.remark = sale.get('remark', '')

                    items = [(0, 0, {
                        'item_seq': item['itemSeq'],
                        'item_cd': item['itemCd'],
                        'item_nm': item['itemNm'],
                        'qty': item['qty'],
                        'prc': item['prc'],
                        'tot_amt': item['totAmt'],
                    }) for item in sale['itemList']]
                    self.item_list = items
                    self.fetched = True
                    break
        else:
            _logger.error('Failed to fetch data: %s', result.get('resultMsg'))
            raise UserError(_('Failed to fetch data: %s') % result.get('resultMsg'))

    def confirm_invoice(self):
        # product_obj = self.env['product.product']
        # for item in self.item_list:
        #     product = product_obj.search([('default_code', '=', item.item_cd)], limit=1)
        #     if product:
        #         product.qty_available += item.qty
        #         _logger.info('Updated product %s with new quantity %s', product.name, product.qty_available)
        #     else:
        #         new_product = product_obj.create({
        #             'name': item.item_nm,
        #             'default_code': item.item_cd,
        #             'type': 'product',
        #             'categ_id': self.env.ref('product.product_category_all').id,
        #             'list_price': item.prc,
        #             'qty_available': item.qty,
        #             # 'useYn': 'Y',
        #         })
        #         _logger.info('Created new product %s with initial quantity %s', new_product.name, new_product.qty_available)

        self._save_purchase()
        self._save_item()
        self._save_stock_master()
        self.status = 'confirmed'
        _logger.info('Invoice confirmed for supplier invoice no: %s', self.spplr_invc_no)

    def _save_purchase(self):
        url = "http://localhost:8085/trnsPurchase/savePurchase"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "invcNo": self.spplr_invc_no,
            "orgInvcNo": 0,
            "spplrTpin": self.spplr_tpin,
            "spplrBhfId": self.spplr_bhf_id,
            "spplrNm": self.spplr_nm,
            "spplrInvcNo": self.spplr_invc_no,
            "regTyCd": 'A',
            "pchsTyCd": "N",
            "rcptTyCd": "P",
            "pmtTyCd": self.pmt_ty_cd,
            "pchsSttsCd": "02",
            "cfmDt": self.cfm_dt.strftime('%Y%m%d%H%M%S'),
            "pchsDt": self.cfm_dt.strftime('%Y%m%d'),
            "wrhsDt": "",
            "cnclReqDt": "",
            "cnclDt": "",
            "rfdDt": "",
            "totItemCnt": self.tot_item_cnt,
            "totTaxblAmt": self.tot_taxbl_amt,
            "totTaxAmt": self.tot_tax_amt,
            "totAmt": self.tot_amt,
            "remark": self.remark or "",
            "regrId": self.create_uid.id,
            "regrNm": self.create_uid.name,
            "modrNm": self.create_uid.name,
            "modrId": self.create_uid.id,
            "itemList": [{
                "itemSeq": item.item_seq,
                "itemCd": item.item_cd,
                "itemClsCd": item.item_cls_cd if item.item_cls_cd else 5059690800,
                "spplrItemClsCd": item.spplr_item_cls_cd if item.spplr_item_cls_cd else None,
                "spplrItemCd": item.spplr_item_cd if item.spplr_item_cd else None,
                "spplrItemNm": item.spplr_item_nm if item.spplr_item_nm else None,
                "pkgUnitCd": item.pkg_unit_cd if item.pkg_unit_cd else 'NT',
                "itemNm": item.spplr_item_nm if item.spplr_item_nm else self.spplr_nm,
                "bcd": "",
                "pkg": item.pkg,
                "qtyUnitCd": item.qty_unit_cd if item.qty_unit_cd else 'U',
                "qty": item.qty,
                "prc": item.prc,
                "splyAmt": item.sply_amt,
                "dcRt": item.dc_rt,
                "dcAmt": item.dc_amt,
                "vatCatCd": item.vat_cat_cd,
                "iplCatCd": item.ipl_cat_cd if item.ipl_cat_cd else None,
                "tlCatCd": item.tl_cat_cd if item.tl_cat_cd else None,
                "exciseTxCatCd": item.excise_tx_cat_cd if item.excise_tx_cat_cd else None,
                "taxAmt": item.tax_amt,
                "taxblAmt": 0,
                "totAmt": item.tot_amt,
                "itemExprDt": item.item_expr_dt if item.item_expr_dt else None
            } for item in self.item_list]
        }

        # print('Payload being sent:', json.dumps(payload, indent=4))

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print('Purchase saved successfully:', response.json())
        except requests.exceptions.RequestException as e:
            _logger.error('Error saving purchase: %s', e)
            if e.response:
                _logger.error('Response content: %s', e.response.content.decode())
            raise UserError(_('Error Check Network/internet Connectivity.'))

    def _save_item(self):
        url = "http://localhost:8085/stock/saveStockItems"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "sarNo": 1,
            "orgSarNo": 0,
            "regTyCd": "M",
            "custTpin": None,
            "custNm": None,
            "custBhfId": self.spplr_bhf_id,
            "sarTyCd": "13",
            "ocrnDt": self.sales_dt.strftime('%Y%m%d'),
            "totItemCnt": len(self.item_list),
            "totTaxblAmt": self.tot_taxbl_amt,
            "totTaxAmt": self.tot_tax_amt,
            "totAmt": self.tot_amt,
            "remark": self.remark or "",
            "regrId": self.create_uid.id,
            "regrNm": self.create_uid.name,
            "modrNm": self.create_uid.name,
            "modrId": self.create_uid.id,
            "itemList": [{
                "itemSeq": item.item_seq,
                "itemCd": item.item_cd,
                "itemClsCd": item.item_cls_cd,
                "itemNm": item.item_nm,
                "bcd": item.bcd,
                "pkgUnitCd": item.pkg_unit_cd,
                "pkg": item.pkg,
                "qtyUnitCd": item.qty_unit_cd,
                "qty": item.qty,
                "itemExprDt": item.item_expr_dt,
                "prc": item.prc,
                "splyAmt": item.sply_amt,
                "totDcAmt": item.tot_dc_amt,
                "taxblAmt": item.taxbl_amt,
                "vatCatCd": item.vat_cat_cd,
                "iplCatCd": item.ipl_cat_cd,
                "tlCatCd": item.tl_cat_cd,
                "exciseTxCatCd": item.excise_tx_cat_cd,
                "vatAmt": item.vat_amt,
                "iplAmt": item.ipl_amt,
                "tlAmt": item.tl_amt,
                "exciseTxAmt": item.excise_tx_amt,
                "taxAmt": item.tax_amt,
                "totAmt": item.tot_amt
            } for item in self.item_list]
        }
        print('Payload being sent:', json.dumps(payload, indent=4))
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print('Stock items saved successfully:', response.json())
        except requests.exceptions.RequestException as e:
            _logger.error('Error saving stock items: %s', e)
            raise UserError(_('Failed to save stock items.'))

    def _save_stock_master(self):
        url = "http://localhost:8085/stockMaster/saveStockMaster"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "regrId": self.create_uid.id,
            "regrNm": self.create_uid.name,
            "modrNm": self.create_uid.name,
            "modrId": self.create_uid.id,
            "stockItemList": [{
                "itemCd": item.item_cd,
                "rsdQty": item.qty
            } for item in self.item_list]
        }
        print('Payload being sent:', json.dumps(payload, indent=4))
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print('Stock master saved successfully:', response.json())
        except requests.exceptions.RequestException as e:
            _logger.error('Error saving stock master: %s', e)
            raise UserError(_('Failed to save stock master data.'))


class PurchaseItem(models.Model):
    _name = 'purchase.item'
    _description = 'Purchase Item'

    purchase_id = fields.Many2one('purchase.data', string='Purchase Data')
    item_seq = fields.Integer(string='Item Sequence')
    item_cd = fields.Char(string='Item Code')
    item_nm = fields.Char(string='Item Name')
    qty = fields.Float(string='Quantity')
    prc = fields.Float(string='Price')
    sply_amt = fields.Float(string='Supply Amount')
    dc_rt = fields.Float(string='Discount Rate')
    dc_amt = fields.Float(string='Discount Amount')
    vat_cat_cd = fields.Char(string='VAT Category Code')
    vat_taxbl_amt = fields.Float(string='VAT Taxable Amount')
    tot_amt = fields.Float(string='Total Amount')
    item_cls_cd = fields.Char(string='Item Class Code')
    spplr_item_cls_cd = fields.Char(string='Supplier Item Class Code')
    spplr_item_cd = fields.Char(string='Supplier Item Code')
    spplr_item_nm = fields.Char(string='Supplier Item Name')
    pkg_unit_cd = fields.Char(string='Package Unit Code')  # Added this field
    pkg = fields.Float(string='Package')  # Add this field if not defined
    qty_unit_cd = fields.Char(string='Quantity Unit Code')  # Add this field if not defined
    item_expr_dt = fields.Date(string='Item Expiry Date')  # Add this field if not defined
    sply_amt = fields.Float(string='Supply Amount')
    tot_dc_amt = fields.Float(string='Total Discount Amount')
    vat_amt = fields.Float(string='VAT Amount')
    ipl_cat_cd = fields.Char(string='IPL Category Code')
    tl_cat_cd = fields.Char(string='TL Category Code')
    excise_tx_cat_cd = fields.Char(string='Excise Tax Category Code')
    ipl_amt = fields.Float(string='IPL Amount')
    tl_amt = fields.Float(string='TL Amount')
    excise_tx_amt = fields.Float(string='Excise Tax Amount')
    tax_amt = fields.Float(string='Tax Amount')
    bcd = fields.Char(string='bcd')
    taxbl_amt = fields.Char(string='taxbl_amt')
