from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import requests

_logger = logging.getLogger(__name__)

VALID_TAX_DESCRIPTIONS = ['A', 'B', 'C1', 'C2', 'C3', 'D', 'RVAT', 'E', 'TOT']


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    classification = fields.Many2one('zra.item.data', string='Item Classification')
    item_cls_cd = fields.Char(string='Item Classification Code', readonly=True, store=True)
    item_cls_lvl = fields.Integer(string='Item Classification Level', readonly=True, store=True)
    tax_ty_cd = fields.Char(string='Tax Type Code', readonly=True, store=True)
    mjr_tg_yn = fields.Char(string='Major Target', readonly=True, store=True)
    use_yn = fields.Char(string='Use', readonly=True, store=True)
    quantity_unit_cdNm = fields.Many2one('quantity.unit.data', string='Quantity Unit')
    quantity_unit_cd = fields.Char(string="Quantity Unit Code", readonly=True, store=True)
    packaging_data_cdNm = fields.Many2one('packaging.unit.data', string='Packaging Unit')
    packaging_unit_cd = fields.Char(string='Packaging Code', readonly=True, store=True)
    cdNm = fields.Many2one('country.data', string='Country')
    cd = fields.Char(string='Origin Country Code', readonly=True, store=True)
    item_Cd = fields.Char(string='Item Code', readonly=False, store=True)

    taxes_id = fields.Many2many(
        'account.tax',
        default=lambda self: self.env['account.tax'].search([('description', '=', 'A')], limit=1).ids
    )

    is_updating = fields.Boolean(default=False, store=False)

    detailed_type = fields.Selection(
        selection=[
            ('product', 'Storable Product'),
            ('consu', 'Consumable'),
            ('service', 'Service'),
        ],
        default='product',
        string='Product Type',
    )

    def copy(self, default=None):
        # Set item code to blank during duplication
        default = dict(default or {}, item_Cd="")
        return super(ProductTemplate, self).copy(default)


    @api.depends('detailed_type')
    def _compute_type(self):
        type_mapping = {
            'product': 'product',
            'consu': 'consu',
            'service': 'service',
        }
        for record in self:
            record.type = type_mapping.get(record.detailed_type, record.detailed_type)

    def get_primary_tax(self):
        # If 'self' is an instance of product.template, use 'self' directly
        if self.taxes_id:
            return self.taxes_id[0]
        return None

    def get_tax_description(self, tax):
        return tax.description if tax else ''

    @api.onchange('taxes_id')
    def _onchange_taxes_id(self):
        self.validate_taxes()
        self.validate_single_tax()

    def validate_taxes(self):
        """Validate that the selected taxes have a valid description."""
        for tax in self.taxes_id:
            if tax.description not in VALID_TAX_DESCRIPTIONS:
                raise ValidationError(
                    _('The selected tax "%s" tax is not valid. Please select a valid tax.') % tax.description)

    def validate_single_tax(self):
        """Ensure that only one tax is selected."""
        if len(self.taxes_id) > 1:
            raise ValidationError(_('You can only add one tax to a product. Please remove the extra taxes.'))

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductTemplate, self)._fields_view_get(view_id, view_type, toolbar, submenu)
        if view_type == 'form':
            detailed_type_field = res['fields'].get('detailed_type', {})
            selection = detailed_type_field.get('selection', [])
            for i, (value, label) in enumerate(selection):
                if value == 'product':
                    selection[i] = (value, 'Storable Product')
            detailed_type_field['selection'] = selection
        return res

    def generate_item_code(self, cd, product_type, packaging_unit, quantity_unit):
        cd = cd if cd else "ISW"
        product_type = product_type if product_type else ""
        packaging_unit = packaging_unit if packaging_unit else ""
        quantity_unit = quantity_unit if quantity_unit else ""

        # Generate the initial item code
        sequence = self.env['item.code.sequence'].search([], limit=1)
        if not sequence:
            sequence = self.env['item.code.sequence'].create({})

        next_number = sequence.next_number
        next_number_str = str(next_number).zfill(7)  # 7-digit zero-padded number
        item_code = f"{cd}{product_type}{packaging_unit}{quantity_unit}{next_number_str}"

        # Check if item code already exists
        existing_code = self.env['product.template'].search([('item_Cd', '=', item_code)], limit=1)
        if existing_code:
            if self._context.get('is_create', False):  # Check if it's a create operation
                # Increment the number to make the code unique
                while self.env['product.template'].search([('item_Cd', '=', item_code)], limit=1):
                    next_number += 1
                    next_number_str = str(next_number).zfill(7)
                    item_code = f"{cd}{product_type}{packaging_unit}{quantity_unit}{next_number_str}"

                # Update the sequence to the new next number
                sequence.next_number = next_number + 1
            else:  # If it's a write operation, raise a validation error
                raise ValidationError(_('Item code "%s" already exists. Please choose a different code.') % item_code)

        # Save the sequence for future use
        sequence.next_number += 1

        return item_code

    @api.onchange('classification')
    def _onchange_classification(self):
        if self.classification:
            self.item_cls_cd = self.classification.itemClsCd
            self.item_cls_lvl = self.classification.itemClsLvl
            self.tax_ty_cd = self.classification.taxTyCd
            self.mjr_tg_yn = self.classification.mjrTgYn
            self.use_yn = self.classification.useYn
        else:
            self.item_cls_cd = False
            self.item_cls_lvl = False
            self.tax_ty_cd = False
            self.mjr_tg_yn = False
            self.use_yn = False

    @api.onchange('quantity_unit_cdNm')
    def _onchange_quantity_unit(self):
        if self.quantity_unit_cdNm:
            self.quantity_unit_cd = self.quantity_unit_cdNm.quantity_unit_cd
        else:
            self.quantity_unit_cd = False

    @api.onchange('packaging_data_cdNm')
    def _onchange_packaging_unit(self):
        if self.packaging_data_cdNm:
            self.packaging_unit_cd = self.packaging_data_cdNm.packaging_unit_cd
        else:
            self.packaging_unit_cd = False

    @api.onchange('cdNm')
    def _onchange_country(self):
        if self.cdNm:
            self.cd = self.cdNm.country_cd
        else:
            self.cd = False

    @api.model
    def create(self, vals):
        _logger.info("Creating product with values: %s", vals)
        vals['is_updating'] = False

        # Ensure that classification, quantity, and packaging codes are properly set before validation
        if 'classification' in vals:
            classification = self.env['zra.item.data'].browse(vals['classification'])
            vals.update({
                'item_cls_cd': classification.itemClsCd,
                'item_cls_lvl': classification.itemClsLvl,
                'tax_ty_cd': classification.taxTyCd,
                'mjr_tg_yn': classification.mjrTgYn,
                'use_yn': classification.useYn
            })
        if 'quantity_unit_cdNm' in vals:
            quantity_unit = self.env['quantity.unit.data'].browse(vals['quantity_unit_cdNm'])
            vals['quantity_unit_cd'] = quantity_unit.quantity_unit_cd
        if 'packaging_data_cdNm' in vals:
            packaging_unit = self.env['packaging.unit.data'].browse(vals['packaging_data_cdNm'])
            vals['packaging_unit_cd'] = packaging_unit.packaging_unit_cd
        if 'cdNm' in vals:
            country = self.env['country.data'].browse(vals['cdNm'])
            vals['cd'] = country.country_cd

        # Validate if the fields are empty after updating the values
        if not vals.get('item_cls_cd'):
            raise ValidationError(_('Item Classification Code is required.'))
        if not vals.get('packaging_unit_cd'):
            raise ValidationError(_('Packaging Unit Code is required.'))
        if not vals.get('cd'):
            raise ValidationError(_('Origin Country Code is required.'))
        if not vals.get('quantity_unit_cd'):
            raise ValidationError(_('Quantity Unit Code is required.'))

        record = super(ProductTemplate, self.with_context(is_create=True)).create(vals)
        record.validate_single_tax()
        record.validate_taxes()
        record._handle_post_item_data(vals, is_create=True)
        _logger.info("Product created with ID: %s", record.id)
        return record

    @api.model
    def write(self, vals):
        if self.env.context.get('is_create', False):
            # Prevent write operations if it's a creation
            return super(ProductTemplate, self).write(vals)

        # Validate if item_Cd already exists
        if 'item_Cd' in vals and self.env['product.template'].search(
                [('item_Cd', '=', vals['item_Cd']), ('id', '!=', self.id)], limit=1):
            raise ValidationError(
                _('Item code "%s" already exists. Please choose a different code.') % vals['item_Cd'])

        _logger.info("Updating product with values: %s", vals)

        # Perform other updates
        if 'cdNm' in vals:
            country = self.env['country.data'].browse(vals['cdNm'])
            vals['cd'] = country.country_cd

        if 'classification' in vals:
            classification = self.env['zra.item.data'].browse(vals['classification'])
            vals.update({
                'item_cls_cd': classification.itemClsCd,
                'item_cls_lvl': classification.itemClsLvl,
                'tax_ty_cd': classification.taxTyCd,
                'mjr_tg_yn': classification.mjrTgYn,
                'use_yn': classification.useYn
            })

        if 'quantity_unit_cdNm' in vals:
            quantity_unit = self.env['quantity.unit.data'].browse(vals['quantity_unit_cdNm'])
            vals['quantity_unit_cd'] = quantity_unit.quantity_unit_cd

        if 'packaging_data_cdNm' in vals:
            packaging_unit = self.env['packaging.unit.data'].browse(vals['packaging_data_cdNm'])
            vals['packaging_unit_cd'] = packaging_unit.packaging_unit_cd

        # Now save the data
        result = super(ProductTemplate, self).write(vals)

        # Perform any post-write operations
        self.validate_single_tax()
        self.validate_taxes()
        self._handle_post_item_data(vals, is_create=False)

        _logger.info("Product updated with ID: %s", self.id)
        return result


    def _handle_post_item_data(self, vals, is_create):
        config_settings = self.env['purchase.data'].sudo().search([], limit=1)

        if not config_settings:
            raise ValidationError("Configuration settings not found.")

        # Log the URLs for debugging
        _logger.info(f"Inventory Endpoint: {config_settings.inventory_endpoint}")
        _logger.info(f"Inventory Update Endpoint: {config_settings.inventory_update_endpoint}")

        if is_create:
            url = config_settings.inventory_endpoint
            success_message = "API Response Item registered"
        else:
            url = config_settings.inventory_update_endpoint
            success_message = "API Response Item updated"

        if not url:
            raise ValidationError("URL is not set. Please configure the URL in settings.")

        self._post_item_data(vals, url, success_message)

    def _post_item_data(self, vals, url, success_message):
        config_settings = self.env['purchase.data'].sudo().search([], limit=1)
        company = self.env.company
        current_user = self.env.user
        if not self.item_Cd:
            self.item_Cd = self.generate_item_code(self.cd, '2', self.packaging_unit_cd, self.quantity_unit_cd)

        if not url:
            raise ValidationError("URL is not set. Please configure the URL in settings.")

            # Determine if it's a create operation based on the presence of 'createItem' in the URL
        is_create = "createItem" in url

        payload = {
            "tpin": company.tpin,
            "bhfId": company.bhf_id,
            "itemCd": self.item_Cd,
            "itemClsCd": self.item_cls_cd,
            "itemTyCd": "2",
            "itemNm": self.name,
            "itemStdNm": self.name,
            "orgnNatCd": self.cd,
            "pkgUnitCd": self.packaging_unit_cd,
            "qtyUnitCd": self.quantity_unit_cd,
            "vatCatCd": self.get_tax_description(self.get_primary_tax()),
            "btchNo": None,
            "bcd": None,
            "dftPrc": self.list_price,
            "addInfo": None,
            "sftyQty": None,
            "isrcAplcbYn": "N",
            "useYn": 'Y' if self.use_yn else 'N',
            "regrNm": current_user.name,
            "regrId": current_user.id,
            "modrNm": current_user.name,
            "modrId": current_user.id
        }
        headers = {'Content-Type': 'application/json'}

        # Additional payload modifications for update cases
        if not is_create:
            payload.update({
                "iplCatCd": "IPL1",
                "tlCatCd": "TL",
                "exciseTxCatCd": "EXEEG"
            })

        _logger.info(f"Using URL: {url}")

        # Check if 'updateItem' is part of the URL and update the payload accordingly
        if 'updateItem' in url:
            payload.update({
                "iplCatCd": "IPL1",
                "tlCatCd": "TL",
                "exciseTxCatCd": "EXEEG"
            })
        print(payload)

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
            # self.print(vals, error_message)
            self.message_post(
                body=f"Exception occurred: {error_message}\nProduct Name: {self.name}, Classification Code: {self.item_cls_cd}")
            self.action_client_action(error_message, 'danger')

    def action_client_action(self, message, message_type):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Notification'),
                'message': message,
                'type': message_type,
                'sticky': False
            }
        }


class ItemCodeSequence(models.Model):
    _name = 'item.code.sequence'
    _description = 'Item Code Sequence'

    next_number = fields.Integer(default=1)
