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
    item_cls_cd = fields.Char(string='Item Classification Code', compute='_compute_classification_data', store=True)
    item_cls_lvl = fields.Integer(string='Item Classification Level', compute='_compute_classification_data', store=True)
    tax_ty_cd = fields.Char(string='Tax Type Code', compute='_compute_classification_data', store=True)
    mjr_tg_yn = fields.Char(string='Major Target', compute='_compute_classification_data', store=True)
    use_yn = fields.Char(string='Use', compute='_compute_classification_data', store=True)

    cdNm = fields.Selection(
        selection='_get_country_options',
        string='Country',
        required=True
    )
    cd = fields.Char(string='Origin Country Code', compute='_compute_country_data', readonly=True)

    @api.model
    def _get_classification_options(self):
        classification_data = self.env['zra.item.save'].fetch_classification_data()
        _logger.info("Classification Data: %s", classification_data)
        unique_classification_data = list(set([(item[0], item[0]) for item in classification_data]))
        return unique_classification_data

    @api.model
    def _get_country_options(self):
        country_data = self.env['country.data'].fetch_country_data()
        _logger.info("Country Data: %s", country_data)
        unique_country_data = list(set([(item[0], item[0]) for item in country_data]))
        return unique_country_data

    @api.depends('classification')
    def _compute_classification_data(self):
        classification_data = {item[0]: item[1] for item in self.env['zra.item.save'].fetch_classification_data()}
        for record in self:
            selected_data = classification_data.get(record.classification)
            if selected_data:
                record.item_cls_cd = selected_data['itemClsCd']
                record.use_yn = selected_data['useYn']
            else:
                record.item_cls_cd = ''
                record.use_yn = ''

    @api.onchange('cdNm')
    def _compute_country_data(self):
        country_data = {item[0]: item[1] for item in self.env['country.data'].fetch_country_data()}
        for record in self:
            selected_data = country_data.get(record.cdNm)
            if selected_data:
                record.cd = selected_data['cd']
            else:
                record.cd = ''

    @api.model
    def create(self, vals):
        if 'cdNm' in vals:
            country = dict(self._get_country_options())
            vals['cd'] = country.get(vals['cdNm'], '')
        context = dict(self.env.context or {})
        context['skip_write'] = True
        record = super(ProductTemplate, self.with_context(context)).create(vals)
        record._handle_post_item_data(vals, is_create=True)
        return record

    def write(self, vals):
        if self.env.context.get('skip_write'):
            return super(ProductTemplate, self).write(vals)
        result = super(ProductTemplate, self).write(vals)
        self._handle_post_item_data(vals, is_create=False)
        return result

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
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "itemCd": "ZM2NTBA0000019",
            "itemClsCd": self.item_cls_cd,
            "itemTyCd": "2",
            "itemNm": self.name,
            "itemStdNm": self.name,
            "orgnNatCd": self.cd,
            "pkgUnitCd": "NT",
            "qtyUnitCd": "U",
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

    def _log_error(self, vals, error_message):
        log_file_path = '/var/log/odoo/zra_smart_invoice_error_log.csv'
        with open(log_file_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([vals.get("default_code", ""), error_message])

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
