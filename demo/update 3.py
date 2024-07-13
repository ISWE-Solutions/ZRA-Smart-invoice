from odoo import models, fields, api, _
import requests
import logging
import csv

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    classification = fields.Selection(
        selection='_get_classification_options',
        string='Item Classification',
        required=True
    )

    quantity_unit_cd = fields.Char(string="Quantity Unit Code")
    item_cls_cd = fields.Char(string='Item Classification Code')
    packaging_unit_cd = fields.Char(string='Packaging Code')
    cd = fields.Char(string='Country Code')

    item_cls_lvl = fields.Integer(string='Item Classification Level', compute='_compute_classification_data',
                                  store=True)
    tax_ty_cd = fields.Char(string='Tax Type Code', compute='_compute_classification_data', store=True)
    mjr_tg_yn = fields.Char(string='Major Target', compute='_compute_classification_data', store=True)
    use_yn = fields.Char(string='Use', compute='_compute_classification_data', store=True)

    quantity_unit_cdNm = fields.Selection(
        selection='_get_quantity_options',
        string='Quantity Unit',
        required=True
    )

    packaging_data_cdNm = fields.Selection(
        selection='_get_packaging_data',
        string='Packaging Unit',
        required=True
    )

    cdNm = fields.Selection(
        selection='_get_country_options',
        string='Country',
        required=True
    )

    item_Cd = fields.Char(string='Item Code', readonly=True, store=True)

    def _compute_fields_if_needed(self, vals):
        """Computes necessary fields based on the provided values."""
        if 'classification' in vals and not vals.get('item_cls_cd'):
            self._compute_classification_data(vals)
        if 'quantity_unit_cdNm' in vals and not vals.get('quantity_unit_cd'):
            self._compute_quantity_unit_data(vals)
        if 'packaging_data_cdNm' in vals and not vals.get('packaging_unit_cd'):
            self._compute_packaging_unit_data(vals)
        if 'cdNm' in vals and not vals.get('cd'):
            self._compute_country_data(vals)

    def generate_item_code(self, cd, product_type, packaging_unit, quantity_unit):
        sequence = self.env['item.code.sequence'].search([], limit=1)
        if not sequence:
            sequence = self.env['item.code.sequence'].create({})

        next_number = sequence.next_number
        sequence.next_number += 1

        next_number_str = str(next_number).zfill(7)
        item_code = f"{cd}{product_type}{packaging_unit}{quantity_unit}{next_number_str}"
        return item_code

    @api.model
    def _get_classification_options(self):
        classification_data = self.env['zra.item.save'].fetch_classification_data()
        unique_classification_data = list(set([(item[0], item[0]) for item in classification_data]))
        return unique_classification_data

    @api.model
    def _get_country_options(self):
        country_data = self.env['country.data'].fetch_country_data()
        unique_country_data = list(set([(item[0], item[0]) for item in country_data]))
        return unique_country_data

    @api.model
    def _get_quantity_options(self):
        quantity_options = self.env['quantity.data'].fetch_quantity_data()
        unique_qua_data = list(set([(item[0], item[0]) for item in quantity_options]))
        return unique_qua_data

    @api.model
    def _get_packaging_data(self):
        packaging_units = self.env['packaging.units'].fetch_packing_data()
        unique_packaging_units = list(set([(item[0], item[0]) for item in packaging_units]))
        return unique_packaging_units

    @api.depends('classification')
    def _compute_classification_data(self, vals=None):
        classification_data = {item[0]: item[1] for item in self.env['zra.item.save'].fetch_classification_data()}
        for record in self:
            if vals:
                classification = vals.get('classification', record.classification)
                item_cls_cd = vals.get('item_cls_cd', record.item_cls_cd)
            else:
                classification = record.classification
                item_cls_cd = record.item_cls_cd

            selected_data = classification_data.get(classification)
            if selected_data and not item_cls_cd:
                record.item_cls_cd = selected_data['itemClsCd']
                record.use_yn = selected_data['useYn']
            else:
                record.item_cls_cd = item_cls_cd if item_cls_cd else ''
                record.use_yn = record.use_yn if record.use_yn else ''

    @api.onchange('cdNm')
    def _compute_country_data(self, vals=None):
        country_data = {item[0]: item[1] for item in self.env['country.data'].fetch_country_data()}
        for record in self:
            if vals:
                cdNm = vals.get('cdNm', record.cdNm)
            else:
                cdNm = record.cdNm

            selected_data = country_data.get(cdNm)
            if selected_data:
                record.cd = selected_data['cd']
            else:
                record.cd = ''

    @api.onchange('quantity_unit_cdNm')
    def _compute_quantity_unit_data(self, vals=None):
        qua_data = {item[0]: item[1] for item in self.env['quantity.data'].fetch_quantity_data()}
        for record in self:
            if vals:
                quantity_unit_cdNm = vals.get('quantity_unit_cdNm', record.quantity_unit_cdNm)
            else:
                quantity_unit_cdNm = record.quantity_unit_cdNm

            selected_data = qua_data.get(quantity_unit_cdNm)
            if selected_data:
                record.quantity_unit_cd = selected_data['quantity_unit_cd']
            else:
                record.quantity_unit_cd = ''

    @api.onchange('packaging_data_cdNm')
    def _compute_packaging_unit_data(self, vals=None):
        packaging_data = {item[0]: item[1] for item in self.env['packaging.units'].fetch_packing_data()}
        for record in self:
            if vals:
                packaging_data_cdNm = vals.get('packaging_data_cdNm', record.packaging_data_cdNm)
            else:
                packaging_data_cdNm = record.packaging_data_cdNm

            selected_data = packaging_data.get(packaging_data_cdNm)
            if selected_data:
                record.packaging_unit_cd = selected_data['packaging_unit_cd']
            else:
                record.packaging_unit_cd = ''

    @api.model
    def create(self, vals):
        self._compute_fields_if_needed(vals)
        return super().create(vals)

    def write(self, vals):
        self._compute_fields_if_needed(vals)
        return super().write(vals)

    def _handle_post_item_data(self, vals, is_create):
        if is_create:
            url = 'http://localhost:8085/items/saveItem'
            success_message = "API Response Item registered"
        else:
            url = 'http://localhost:8085/items/updateItem'
            success_message = "API Response Item updated"

        self._post_item_data(vals, url, success_message)

    def _post_item_data(self, vals, url, success_message):
        current_user = self.env.user
        if not self.item_Cd:
            self.item_Cd = self.generate_item_code(self.cd, '2', self.packaging_unit_cd, self.quantity_unit_cd)

        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "itemCd": self.item_Cd,
            "itemClsCd": self.item_cls_cd,
            "itemTyCd": "2",
            "itemNm": self.name,
            "itemStdNm": self.name,
            "orgnNatCd": self.cd,
            "pkgUnitCd": self.packaging_unit_cd,
            "qtyUnitCd": self.quantity_unit_cd,
            "vatCatCd": "A",
            "btchNo": None,
            "bcd": None,
            "dftPrc": self.list_price,
            "addInfo": None,
            "sftyQty": None,
            "isrcAplcbYn": "N",
            "useYn": self.use_yn,
            "regrNm": current_user.name,
            "regrId": current_user.id,
            "modrNm": current_user.name,
            "modrId": current_user.id
        }
        headers = {'Content-Type': 'application/json'}

        if 'updateItem' in url:
            payload.update({
                "iplCatCd": "IPL1",
                "tlCatCd": "TL",
                "exciseTxCatCd": "EXEEG"
            })

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result_data = response.json()
            result_msg = result_data.get("resultMsg")
            self.message_post(
                body=f"{success_message}: {result_msg}, \nProduct Name: {self.name}, Classification Code: {self.item_cls_cd}")
            self.action_client_action(result_msg, 'success')
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            self._log_error(vals, error_message)
            self.message_post(
                body=f"Exception occurred: {error_message}\nProduct Name: {self.name}, Classification Code: {self.item_cls_cd}")
            self.action_client_action(error_message, 'danger')

    def action_client_action(self, message, message_type):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Notification'),
                'type': message_type,
                'sticky': False
            }
        }


class ItemCodeSequence(models.Model):
    _name = 'item.code.sequence'
    _description = 'Item Code Sequence'

    next_number = fields.Integer('Next Number', default=1)
