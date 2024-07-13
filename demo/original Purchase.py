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
    quantity_unit_cd = fields.Char(string="Quantity Unit Code")
    cd = fields.Char(string='Country Code')
    item_nm = fields.Char(string='Item Name')
    location_id = fields.Many2one('stock.location', string='Location', required=False)
    tot_tax_amt = fields.Float(string='Total Tax Amount')
    tot_amt = fields.Float(string='Total Amount')
    remark = fields.Text(string='Remark')
    item_list = fields.One2many('purchase.item', 'purchase_id', string='Item List')
    fetched = fields.Boolean(string="Fetched", default=False)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
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
            return []

        try:
            result = response.json()
        except ValueError as e:
            _logger.error('Error parsing JSON response: %s', e)
            return []

        if result.get('resultCd') == '000':
            sale_list = result['data'].get('saleList', [])
            existing_invoices = self.search([]).mapped('spplr_invc_no')
            new_options = [(str(sale['spplrInvcNo']), f"{sale['spplrNm']} - {sale['spplrTpin']}") for sale in sale_list
                           if sale['spplrInvcNo'] and sale['spplrInvcNo'] not in existing_invoices]
            return new_options
        else:
            _logger.error('Failed to fetch data: %s', result.get('resultMsg'))
            return []

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
            raise UserError(_('Failed to fetch data from the endpoint: %s') % e)

        try:
            result = response.json()
        except ValueError as e:
            raise UserError(_('Failed to parse response from the endpoint: %s') % e)

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

                    def parse_date(date_str):
                        if not date_str:
                            return None
                        for fmt in ('%Y%m%d%H%M%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d'):
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                pass
                        raise ValueError(f"Date format for {date_str} is not supported")

                    self.cfm_dt = parse_date(sale['cfmDt']) if sale.get('cfmDt') else None
                    self.sales_dt = parse_date(sale['salesDt']).date() if sale.get('salesDt') else None
                    self.stock_rls_dt = parse_date(sale['stockRlsDt']) if sale.get('stockRlsDt') else None

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
                        'qty_unit_cd': item['qtyUnitCd'],
                        'item_cls_cd': item['itemClsCd'],
                        'pkg_unit_cd': item['pkgUnitCd'],
                    }) for item in sale['itemList']]
                    self.item_list = items
                    self.fetched = True
                    break
        else:
            raise UserError(_('Failed to fetch data: %s') % result.get('resultMsg'))

    def confirm_invoice(self):
        _logger.info('Confirming invoice for supplier invoice no: %s', self.spplr_invc_no)

        # Ensure location is set
        if not self.location_id:
            # Check if any locations exist
            all_locations = self.env['stock.location'].search([])
            if not all_locations:
                _logger.warning('No locations found in the system. Creating a default location.')

                # Create a default location if none exist
                location_vals = {
                    'name': 'WH/Stock',
                    'location_id': self.env.ref('stock.stock_location_stock').id,
                    # Assign parent location, adjust as necessary
                    'usage': 'internal',
                }
                location = self.env['stock.location'].create(location_vals)
                _logger.info('Created default location %s (ID: %s)', location.name, location.id)
            else:
                # Search for a default location by name
                location = self.env['stock.location'].search([('name', '=', 'WH/Stock')], limit=1)
                if not location:
                    _logger.warning('Default location "WH/Stock" not found. Creating it.')

                    # Create the default location if it doesn't exist
                    location_vals = {
                        'name': 'WH/Stock',
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        # Assign parent location, adjust as necessary
                        'usage': 'internal',
                    }
                    location = self.env['stock.location'].create(location_vals)
                    _logger.info('Created default location %s (ID: %s)', location.name, location.id)

            self.location_id = location.id
            _logger.info('Location automatically set to %s (ID: %s)', location.name, location.id)

        product_category = self.env.ref('product.product_category_all')
        if not product_category:
            raise UserError(_('Default product category not found.'))

        StockQuant = self.env['stock.quant']
        for item in self.item_list:
            _logger.info('Processing item: %s', item.item_cd)

            product_template = self.env['product.template'].search(
                [('item_Cd', '=', item.item_cd), ('name', '=', item.item_nm)], limit=1)
            if product_template:
                product = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)], limit=1)
                if product:
                    # Find the stock quant for the product and location
                    stock_quant = StockQuant.search(
                        [('product_id', '=', product.id), ('location_id', '=', self.location_id.id)], limit=1)
                    if stock_quant:
                        stock_quant.quantity += item.qty
                        _logger.info('Updated quantity for product %s to %s', product_template.name,
                                     stock_quant.quantity)
                    else:
                        # If no quant exists, create one
                        StockQuant.create({
                            'product_id': product.id,
                            'location_id': self.location_id.id,
                            'quantity': item.qty,
                        })
                        _logger.info('Created new stock quant for product %s with quantity %s', product_template.name,
                                     item.qty)
            else:
                try:
                    new_product_template_vals = {
                        'name': item.item_nm,
                        'default_code': item.item_cd,
                        'type': 'product',
                        'categ_id': product_category.id,
                        'list_price': item.prc,
                        'quantity_unit_cd': item.qty_unit_cd,
                        'item_cls_cd': item.item_cls_cd,
                        'packaging_unit_cd': item.pkg_unit_cd,
                        'item_Cd': item.item_cd,
                        'cd': 'ZM',
                        'use_yn': 'Y',
                    }
                    _logger.info('Creating new product template with values: %s', new_product_template_vals)

                    new_product_template = self.env['product.template'].create(new_product_template_vals)
                    new_product = self.env['product.product'].search(
                        [('product_tmpl_id', '=', new_product_template.id)], limit=1)

                    # Create a stock quant for the new product
                    StockQuant.create({
                        'product_id': new_product.id,
                        'location_id': self.location_id.id,
                        'quantity': item.qty,
                    })
                    _logger.info('Created new product template %s with initial quantity %s', new_product_template.name,
                                 item.qty)
                except Exception as e:
                    _logger.error('Error creating product: %s', str(e))
                    raise UserError(_('Error creating product: %s') % str(e))

        self._save_purchase()
        self._save_item()
        self._save_stock_master()
        self.status = 'confirmed'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Invoice confirmed for supplier invoice no: %s') % self.spplr_invc_no,
                'sticky': False,
            }
        }

    def reject_purchase(self):
        self._reject_purchase()
        self.status = 'rejected'
        _logger.info('Invoice confirmed for supplier invoice no: %s', self.spplr_invc_no)

    def _reject_purchase(self):
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
            "rcptTyCd": "R",
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
                "vatCatCd": item.vat_cat_cd if item.ipl_cat_cd else 'A',
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
                "vatCatCd": item.vat_cat_cd if item.ipl_cat_cd else 'A',
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
            "sarTyCd": "02",
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
                "itemClsCd": item.item_cls_cd if item.item_cls_cd else 5059690800,
                "itemNm": item.item_nm,
                "bcd": item.bcd,
                "pkgUnitCd": item.pkg_unit_cd if item.pkg_unit_cd else 'NT',
                "pkg": item.pkg,
                "qtyUnitCd": item.qty_unit_cd if item.qty_unit_cd else 'U',
                "qty": item.qty,
                "itemExprDt": item.item_expr_dt if item.item_expr_dt else None,
                "prc": item.prc,
                "splyAmt": item.sply_amt,
                "totDcAmt": item.tot_dc_amt,
                "taxblAmt": item.taxbl_amt if item.ipl_cat_cd else 0,
                "vatCatCd": item.vat_cat_cd if item.ipl_cat_cd else 'A',
                "iplCatCd": item.ipl_cat_cd if item.ipl_cat_cd else 'IPL1',
                "tlCatCd": item.tl_cat_cd if item.tl_cat_cd else 'TL',
                "exciseTxCatCd": item.excise_tx_cat_cd if item.excise_tx_cat_cd else 'EXEEG',
                "vatAmt": item.vat_amt,
                "iplAmt": item.ipl_amt,
                "tlAmt": item.tl_amt,
                "exciseTxAmt": item.excise_tx_amt,
                "taxAmt": item.tax_amt if item.tax_amt else 16,
                "totAmt": item.tot_amt
            } for item in self.item_list]
        }
        print('Payload being sent:', json.dumps(payload, indent=4))
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print('Stock items saved successfully:', response.json())
        except requests.exceptions.RequestException as e:
            print('Stock items failed:', response.json())
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
    pkg_unit_cd = fields.Char(string='Package Unit Code')
    cd = fields.Char(string='Country Code')
    pkg = fields.Float(string='Package')
    qty_unit_cd = fields.Char(string='Quantity Unit Code')
    item_expr_dt = fields.Date(string='Item Expiry Date')
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


class ProductProduct(models.Model):
    _inherit = 'product.product'

    quantity_unit_cd = fields.Char(string="Quantity Unit Code")
    item_cls_cd = fields.Char(string="Item Classification Code")
    packaging_unit_cd = fields.Char(string="Packaging Unit Code")
    item_Cd = fields.Char(string="Item Code")
    use_yn = fields.Char(string="Use")
