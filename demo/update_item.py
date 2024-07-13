from odoo import models, fields, api, _
import requests
import csv

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

    origin_country_id = fields.Many2one('res.country', string='Origin Country', default=lambda self: self.env.ref('base.zm'))
    origin_country_cd = fields.Char(string='Origin Country Code', readonly=True)

    @api.onchange('origin_country_id')
    def _onchange_origin_country_id(self):
        self.origin_country_cd = self.origin_country_id.code if self.origin_country_id else ''

    @api.model
    def _get_classification_options(self):
        classification_data = self.env['zra.item.save'].fetch_classification_data()
        return [(item[0], item[0]) for item in classification_data]

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

    @api.model
    def create(self, vals):
        print('Create method called with vals:', vals)
        if 'origin_country_id' in vals:
            country = self.env['res.country'].browse(vals['origin_country_id'])
            vals['origin_country_cd'] = country.code
        context = dict(self.env.context or {})
        context['skip_write'] = True
        record = super(ProductTemplate, self.with_context(context)).create(vals)
        record._handle_post_item_data(vals, is_create=True)
        return record

    def write(self, vals):
        if self.env.context.get('skip_write'):
            return super(ProductTemplate, self).write(vals)
        print('update method called with vals:', vals)
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
        print('Post item data called with URL:', url, 'and vals:', vals)
        current_user = self.env.user
        origin_country_cd = vals.get('origin_country_cd', self.origin_country_cd)
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "itemCd": "ZM2NTBA0000019",
            "itemClsCd": self.item_cls_cd,
            "itemTyCd": "2",
            "itemNm": self.name,
            "itemStdNm": self.name,
            "orgnNatCd": origin_country_cd,
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
            print('Success:', result_msg)
            self.message_post(
                body=f"{success_message}: {result_msg}, \nProduct Name: {self.name}, Classification Code: {self.item_cls_cd}")
            self.action_client_action(result_msg, 'success')
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            print('Failed to post item data:', e)
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
