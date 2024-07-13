from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ImportData(models.Model):
    _name = 'import.data'
    _description = 'Import Data'
    location_id = fields.Many2one('stock.location', string='Location', required=False)
    task_cd = fields.Char(string='Task Code')
    dcl_de = fields.Date(string='Declaration Date')
    dcl_no = fields.Char(string='Declaration Number')
    tot_wt = fields.Float(string='Total Weight')
    net_wt = fields.Float(string='Net Weight')
    agnt_nm = fields.Char(string='Agent Name')
    item_nm = fields.Char(string='Item Name')
    invc_fcur_amt = fields.Float(string='Invoice Foreign Currency Amount')
    invc_fcur_cd = fields.Char(string='Invoice Foreign Currency Code')
    invc_fcur_excrt = fields.Float(string='Invoice Foreign Currency Exchange Rate')
    pkg_unit_cd = fields.Char(string='Package Unit Code')
    cd = fields.Char(string='Package Unit Code')
    orgn_nat_cd = fields.Char(string='original Unit Code')
    qty_unit_cd = fields.Char(string='Quantity Country Code')
    remark = fields.Text(string='Remark')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('refused', 'Refused'),
        ('confirmed', 'Confirmed')
    ], string='Status', default='draft')
    item_list = fields.One2many('import.item', 'import_id', string='Items')
    fetched = fields.Boolean(string='Fetched', default=False)
    fetch_selection = fields.Selection(
        selection='_compute_fetch_selection',
        string='Fetch Selection',
        required=True,
        help="Select an item from the fetched data."
    )

    @api.model
    def _compute_fetch_selection(self):
        api_url = "http://localhost:8085/imports/selectImportItems"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "lastReqDt": "20240105210300"
        }
        response = requests.post(api_url, json=payload)
        if response.status_code != 200:
            return []

        result = response.json()
        if result.get('resultCd') != '000':
            return []

        item_list = result.get('data', {}).get('itemList', [])
        if not item_list:
            return []

        selection_data = [
            (
                f"{item['taskCd']}_{item['itemSeq']}",
                f"{item['itemNm']} - {item['taskCd']} - {item['orgnNatCd']}"
            )
            for item in item_list
        ]

        return selection_data

    @api.onchange('fetch_selection')
    def _onchange_fetch_selection(self):
        if self.fetch_selection:
            self.fetch_import_data()

    def fetch_import_data(self):
        if not self.fetch_selection:
            raise UserError(_('No selection made.'))

        task_cd, item_seq = self.fetch_selection.split('_')

        selected_task_cd = self.fetch_selection

        api_url = "http://localhost:8085/imports/selectImportItems"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "lastReqDt": "20240105210300"
        }

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get('resultCd') != '000':
                raise UserError(_('Error fetching data: %s') % data.get('resultMsg'))

            item_list = data.get('data', {}).get('itemList', [])

            # Filter items based on the selected task_cd
            selected_item = next(
                (item for item in item_list if str(item['taskCd']) == task_cd and str(item['itemSeq']) == item_seq),
                None
            )

            if not selected_item:
                raise UserError(_('Selected item not found in the fetched data.'))

            # Create or update the selected item
            self.create_or_update_import_data(selected_item)

            self.write({
                'fetched': True,
            })

            return {
                'type': 'ir.actions.act_window',
                'name': 'Import Data',
                'res_model': 'import.data',
                'view_mode': 'tree,form',
                'views': [
                    (self.env.ref('zra_smart_invoice.view_import_data_tree').id, 'tree'),
                    (self.env.ref('zra_smart_invoice.view_import_data_form').id, 'form')
                ],
                'target': 'current',
            }
        except requests.exceptions.RequestException as e:
            raise UserError(_('Failed to fetch data: %s') % e)

    def create_or_update_import_data(self, item):
        if not item.get('taskCd') or not item.get('dclNo'):
            _logger.warning('Skipped creation of record due to missing taskCd or dclNo')
            return

        existing_record = self.search([('task_cd', '=', item.get('taskCd')), ('dcl_no', '=', item.get('dclNo'))])
        item_values = {
            'item_seq': item.get('itemSeq'),
            'hs_cd': item.get('hsCd'),
            'item_nm': item.get('itemNm'),
            'pkg': item.get('pkg'),
            'pkg_unit_cd': item.get('pkgUnitCd'),
            'orgn_nat_cd': item.get('orgnNatCd'),  # Ensure this is correctly fetched
            'qty': item.get('qty'),
            'fetched_qty': item.get('qty'),
            'qty_unit_cd': item.get('qtyUnitCd'),
            'tot_wt': item.get('totWt'),
            'net_wt': item.get('netWt'),
            'agnt_nm': item.get('agntNm'),
            'invc_fcur_amt': item.get('invcFcurAmt')
        }

        if existing_record:
            # Update existing record
            existing_record.write({
                'task_cd': item.get('taskCd'),
                'dcl_de': self._parse_date(item.get('dclDe')),
                'dcl_no': item.get('dclNo'),
                'tot_wt': item.get('totWt'),
                'net_wt': item.get('netWt'),
                'agnt_nm': item.get('agntNm'),
                'invc_fcur_amt': item.get('invcFcurAmt'),
                'invc_fcur_cd': item.get('invcFcurCd'),
                'invc_fcur_excrt': item.get('invcFcurExcrt'),
                'remark': item.get('remark'),
                'status': 'draft',
                'fetched': True,
            })

            # Update or create item in item_list
            existing_item = existing_record.item_list.filtered(lambda x: x.item_seq == item.get('itemSeq'))
            if existing_item:
                existing_item.write(item_values)
            else:
                existing_record.write({'item_list': [(0, 0, item_values)]})

        else:
            # Create new record
            vals = {
                'task_cd': item.get('taskCd'),
                'dcl_de': self._parse_date(item.get('dclDe')),
                'dcl_no': item.get('dclNo'),
                'tot_wt': item.get('totWt'),
                'net_wt': item.get('netWt'),
                'agnt_nm': item.get('agntNm'),
                'invc_fcur_amt': item.get('invcFcurAmt'),
                'invc_fcur_cd': item.get('invcFcurCd'),
                'invc_fcur_excrt': item.get('invcFcurExcrt'),
                'remark': item.get('remark'),
                'status': 'draft',
                'fetched': True,
                'item_list': [(0, 0, item_values)]
            }
            self.create(vals)

    def _parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return False

    def action_confirm_import(self):
        self.ensure_one()

        if not self.item_list:
            raise UserError(_('No items to import.'))

        confirmed_qty = sum(item.qty for item in self.item_list)
        fetched_qty = sum(item.fetched_qty for item in self.item_list)
        rejected_qty = confirmed_qty - fetched_qty

        print('fetched', fetched_qty)
        print('confirmed', confirmed_qty)

        if confirmed_qty == 0:
            self.reject_import_items()
        else:
            if confirmed_qty == fetched_qty:
                self.update_import_items()
            else:
                self.update_import_items()
                self.reject_import_items(called_with_update=True)

        self.write({'status': 'confirmed'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Import confirmed for supplier'),
                'sticky': False,
            }
        }

    def create_or_update_products(self):
        product_template_model = self.env['product.template']
        product_product_model = self.env['product.product']
        stock_quant_model = self.env['stock.quant']
        stock_location = self.env.ref('stock.stock_location_stock')  # Adjust this to use the correct stock location

        for item in self.item_list:
            product_name = item.item_nm

            if not product_name:
                continue

            # Check if product template exists, or create a new one
            existing_template = product_template_model.search([('name', '=', product_name)], limit=1)
            template_values = {
                'name': product_name,
                'default_code': item.hs_cd,
                'type': 'product',
                'list_price': item.invc_fcur_amt,
                'standard_price': item.invc_fcur_amt,
                'weight': item.net_wt,
                'packaging_unit_cd': item.pkg_unit_cd,
                'quantity_unit_cd': item.qty_unit_cd,
                'use_yn': 'Y',
                'cd': 'ZA',  # Ensure this is correctly fetched and used
            }

            if existing_template:
                # Update existing product template
                print(f'Updating existing product template {existing_template.name} with values: {template_values}')
                existing_template.write(template_values)
            else:
                # Create new product template
                print(f'Creating new product template with values: {template_values}')
                existing_template = product_template_model.create(template_values)

            # Ensure the product variant exists
            product_variant = product_product_model.search([('product_tmpl_id', '=', existing_template.id)], limit=1)
            if not product_variant:
                product_variant = product_product_model.create({'product_tmpl_id': existing_template.id})

            # Update or create stock quant
            stock_quant = stock_quant_model.search([
                ('product_id', '=', product_variant.id),
                ('location_id', '=', stock_location.id)
            ], limit=1)

            if stock_quant:
                new_quantity = stock_quant.quantity + item.qty
                stock_quant.write({'quantity': new_quantity})
                print(f'Updated stock quant for {product_variant.name}, new quantity: {new_quantity}')
            else:
                stock_quant_model.create({
                    'product_id': product_variant.id,
                    'location_id': stock_location.id,
                    'quantity': item.qty,
                })
                print(f'Created new stock quant for {product_variant.name} with quantity: {item.qty}')

        # Optionally, commit the transaction if necessary
        self.env.cr.commit()

    def confirm_import(self):
        self.write({'status': 'confirmed'})


    def update_import_items(self):
        if not self.item_list:
            raise UserError(_('No items to import.'))

        confirmed_qty = sum(item.qty for item in self.item_list)
        fetched_qty = sum(item.fetched_qty for item in self.item_list)
        rejected_qty = fetched_qty - confirmed_qty
        print('rejected', rejected_qty)

        api_url = "http://localhost:8085/imports/updateImportItems"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "taskCd": self.task_cd,
            "dclDe": self.dcl_de.strftime('%Y%m%d'),
            "importItemList": [{
                "itemSeq": item.item_seq,
                "hsCd": item.hs_cd,
                "itemClsCd": item.item_cls_cd,
                "itemCd": item.item_cd,
                "imptItemSttsCd": "3",
                "remark": item.remark or "remark",
                "modrNm": self.create_uid.name,
                "modrId": self.create_uid.id,
            } for item in self.item_list if item.confirmed_qty > 0]
        }

        self.save_stock_items(confirmed_qty)
        self.save_stock_master(confirmed_qty)

        response = requests.post(api_url, json=payload)
        if response.status_code != 200:
            raise UserError(_('Failed to update import items: HTTP %s') % response.status_code)
        _logger.info('Import items updated: %s', response.json())
        print('Update saved successfully:', response.json())

    def reject_import_items(self, called_with_update=False):
        if not self.item_list:
            raise UserError(_('No items to import.'))

        confirmed_qty = sum(item.qty for item in self.item_list)
        fetched_qty = sum(item.fetched_qty for item in self.item_list)
        rejected_qty = fetched_qty - confirmed_qty

        api_url = "http://localhost:8085/imports/updateImportItems"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "taskCd": self.task_cd,
            "dclDe": self.dcl_de.strftime('%Y%m%d'),
            "importItemList": [{
                "itemSeq": item.item_seq,
                "hsCd": item.hs_cd,
                "itemClsCd": item.item_cls_cd,
                "itemCd": item.item_cd,
                "imptItemSttsCd": "4",
                "remark": item.remark or "",
                "modrNm": self.create_uid.name,
                "modrId": self.create_uid.id,
            } for item in self.item_list if item.qty > item.confirmed_qty]
        }

        response = requests.post(api_url, json=payload)
        if response.status_code != 200:
            raise UserError(_('Failed to update import items: HTTP %s') % response.status_code)
        _logger.info('Import items updated: %s', response.json())
        print('Rejected saved successfully:', response.json())

        if called_with_update:
            self.save_stock_items(rejected_qty)
            self.save_stock_master(rejected_qty)

    def save_stock_items(self, imp_qty):
        api_url = "http://localhost:8085/stock/saveStockItems"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "sarNo": 1,
            "orgSarNo": 0,
            "regTyCd": "M",
            "custTpin": None,
            "custNm": None,
            "custBhfId": "000",
            "sarTyCd": "01",
            "ocrnDt": fields.Date.today().strftime('%Y%m%d'),
            "totItemCnt": len(self.item_list),
            "totTaxblAmt": sum(item.qty * item.invc_fcur_amt for item in self.item_list),
            "totTaxAmt": sum(item.qty * item.invc_fcur_amt * 0.16 for item in self.item_list),
            # Assuming a 12% tax rate
            "totAmt": sum(item.qty * item.invc_fcur_amt for item in self.item_list),
            "remark": self.remark,
            "regrId": self.create_uid.id,
            "regrNm": self.create_uid.name,
            "modrNm": self.create_uid.name,
            "modrId": self.create_uid.id,
            "itemList": [{
                "itemSeq": item.item_seq,
                "itemCd": item.item_cd,
                "itemClsCd": item.item_cls_cd,
                "itemNm": item.item_nm,
                "bcd": None,
                "pkgUnitCd": 'NT',
                "pkg": item.pkg,
                "qtyUnitCd": item.qty_unit_cd,
                "qty": imp_qty or item.qty,
                "itemExprDt": None,
                "prc": item.invc_fcur_amt,
                "splyAmt": item.qty * item.invc_fcur_amt,
                "totDcAmt": 0,
                "taxblAmt": item.qty * item.invc_fcur_amt,
                "vatCatCd": 'A',
                "iplCatCd": None,
                "tlCatCd": None,
                "exciseTxCatCd": None,
                "vatAmt": item.qty * item.invc_fcur_amt * 0.16,
                "iplAmt": item.qty * item.invc_fcur_amt * 0.16,
                "tlAmt": item.qty * item.invc_fcur_amt * 0.16,
                "exciseTxAmt": item.qty * item.invc_fcur_amt * 0.16,
                "taxAmt": 16,
                "totAmt": item.qty * item.invc_fcur_amt
            } for item in self.item_list]
        }

        print("Save Stock Items Payload:")
        print(payload)

        response = requests.post(api_url, json=payload)
        if response.status_code != 200:
            raise UserError(_('Failed to save stock items: HTTP %s') % response.status_code)
        _logger.info('Stock items saved: %s', response.json())
        print('save stock saved successfully:', response.json())

    def save_stock_master(self ,imp_qty):
        api_url = "http://localhost:8085/stockMaster/saveStockMaster"
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "regrId": self.create_uid.id,
            "regrNm": self.create_uid.name,
            "modrNm": self.create_uid.name,
            "modrId": self.create_uid.id,
            "stockItemList": [{
                "itemCd": item.item_cd,
                "rsdQty":imp_qty or item.qty
            } for item in self.item_list]
        }

        print("Save Stock Master Payload:")
        print(payload)

        response = requests.post(api_url, json=payload)

        if response.status_code != 200:
            raise UserError(_('Failed to save stock master: HTTP %s') % response.status_code)
        _logger.info('Stock master saved: %s', response.json())
        print('save master saved successfully:', response.json())


class ImportItem(models.Model):
    _name = 'import.item'
    _description = 'Import Item'

    import_id = fields.Many2one('import.data', string='Import ID')
    item_seq = fields.Integer(string='Item Sequence')
    hs_cd = fields.Char(string='HS Code')
    item_nm = fields.Char(string='Item Name')
    confirmed_qty = fields.Float(string='Confirmed Quantity', default=0.0)
    pkg = fields.Integer(string='Package')
    pkg_unit_cd = fields.Char(string='Package Unit Code')
    qty = fields.Integer(string='Quantity')
    fetched_qty = fields.Integer(string='Quantity')
    qty_unit_cd = fields.Char(string='Quantity Unit Code')
    orgn_nat_cd = fields.Char(string="Original Country Code")
    expt_nat_cd = fields.Char(string="Expected Country Code")
    tot_wt = fields.Float(string='Total Weight')
    net_wt = fields.Float(string='Net Weight')
    agnt_nm = fields.Char(string='Agent Name')
    invc_fcur_amt = fields.Float(string='Invoice Foreign Currency Amount')
    remark = fields.Text(string='Remark')
    item_cls_cd = fields.Char(string='Item Class Code')
    item_cd = fields.Char(string='Item Code')


    @api.depends('import_id.item_list')
    def _compute_confirmed_qty(self):
        for item in self:
            item.confirmed_qty = item.qty