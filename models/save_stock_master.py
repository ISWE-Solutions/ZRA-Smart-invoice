import requests
from odoo import models, api
import logging
import json

_logger = logging.getLogger(__name__)


class StockChangeProductQty(models.TransientModel):
    _inherit = 'stock.change.product.qty'

    def change_product_qty(self):
        config_settings = self.env['res.company'].sudo().search([], limit=1)
        current_user = self.env.user
        _logger.info('Entering change_product_qty method.')
        print('Entering change_product_qty method.')

        res = super(StockChangeProductQty, self).change_product_qty()

        for record in self:
            product = record.product_id
            new_qty = record.new_quantity
            product_template = product.product_tmpl_id

            _logger.info(f'Changing quantity for product: {product.display_name} to {new_qty}')
            print(f'Changing quantity for product: {product.display_name} to {new_qty}')

            # Prepare the payload for the POST request
            company = self.env.company
            payload = {
                "tpin": company.tpin,
                "bhfId": company.bhf_id,
                "regrId": current_user.id,
                "regrNm": current_user.name,
                "modrNm": current_user.name,
                "modrId": current_user.id,
                "stockItemList": [
                    {
                        "itemCd": product_template.item_Cd,
                        "rsdQty": new_qty
                    }
                ]
            }

            try:
                print('Payload being sent:', json.dumps(payload, indent=4))
                # Make the POST request to the given endpoint
                response = requests.post(config_settings.stock_master_endpoint, json=payload)
                response.raise_for_status()
                result_msg = response.json().get('resultMsg', 'No result message received')
                _logger.info(f'Endpoint response: {result_msg}')
                print(f'Endpoint response: {result_msg}')
            except requests.exceptions.RequestException as e:
                result_msg = str(e)
                _logger.error(f'Error during POST request: {result_msg}')
                print(f'Error during POST request: {result_msg}')

            # Post the resultMsg to the chatter
            product_template.message_post(
                body='Quantity of product {} has been updated to {}. Endpoint response: {}'.format(product.display_name,
                                                                                                   new_qty, result_msg),
                subtype_id=self.env.ref('mail.mt_note').id
            )

            _logger.info(f'Message posted for product: {product.display_name} on product.template')
            print(f'Message posted for product: {product.display_name} on product.template')

        _logger.info('Exiting change_product_qty method.')
        print('Exiting change_product_qty method.')

        return res


class StockPickingReturn(models.TransientModel):
    _inherit = 'stock.return.picking'

    def get_sales_order_fields(self):
        """Retrieve tpin, lpo, and export_country_id from related sale order."""
        sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
        return sale_order.tpin, sale_order.lpo, sale_order.export_country_id.code if sale_order.export_country_id else None

    def create_returns(self):
        _logger.info('Entering create_returns method.')
        print('Entering create_returns method.')

        result = super(StockPickingReturn, self).create_returns()
        self._process_return_moves()

        _logger.info('Exiting create_returns method.')
        print('Exiting create_returns method.')

        return result

    def _process_return_moves(self):
        config_settings = self.env['res.company'].sudo().search([], limit=1)
        tpin, lpo, export_country_code = self.get_sales_order_fields()
        current_user = self.env.user

        credit_move = self.env['account.move'].browse(self._context.get('active_id'))
        partner = credit_move.partnerid

        for picking in self.env['stock.picking'].browse(self._context.get('active_ids', [])):
            _logger.info(f'Processing return for picking with type: {picking.picking_type_id.code}')
            print(f'Processing return for picking with type: {picking.picking_type_id.code}')

            if picking.picking_type_id.code in ['incoming', 'outgoing']:
                moves = picking.move_ids_without_package

                for move in moves:
                    product = move.product_id
                    return_qty = move.product_qty  # Quantity being returned

                    _logger.info(f'Processing return move for product: {product.display_name}')
                    print(f'Processing return move for product: {product.display_name}')

                    # Prepare payloads for the POST requests
                    company = self.env.company
                    payload_stock_items = {
                        "tpin": company.tpin,
                        "bhfId": company.bhf_id,
                        "sarNo": 1,
                        "orgSarNo": 0,
                        "regTyCd": "M",
                        "custTpin": tpin or None,
                        "custNm": self.partner_id.mame,
                        "custBhfId": "000",
                        "sarTyCd": "13",
                        "ocrnDt": self.invoive_date.strftime('%Y%m%d') if self.invoice_date else None,
                        "totItemCnt": len(self.invoice_line_ids),
                        "totTaxblAmt": round(sum(line.price_total for line in self.invoice_lines_ids), 2),
                        "totTaxAmt": round(
                            sum(line.price_total - line.price_subtotal for line in self.invoice_line_ids), 2),
                        "totAmt": round(sum(line.price_total for line in self.invoice_line_ids), 2),
                        "remark": None,
                        "regrId": current_user.id,
                        "regrNm": current_user.name,
                        "modrNm": current_user.name,
                        "modrId": current_user.id,
                        "itemList": [
                            {
                                "itemSeq": index + 1,
                                "itemCd": line.product_id.product_tmpl_id.item_Cd,
                                "itemClsCd": line.product_id.product_tmpl_id.item_cls_cd,
                                "itemNm": line.product_id.name,
                                "bcd": line.product_id.barcode or None,
                                "pkgUnitCd": line.product_id.product_tmpl_id.packaging_unit_cd,
                                "pkg": line.quantity,
                                "qtyUnitCd": line.product_id.product_tmpl_id.quantity_unit_cd,
                                "qty": line.quantity,
                                "itemExprDt": None,
                                "prc": round(self.calculate_tax_inclusive_price(line), 2),
                                "splyAmt": round(line.quantity * self.calculate_tax_inclusive_price(line), 2),
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
                                "totAmt": round(line.price_total, 2),
                            } for index, line in enumerate(self.invoice_line_ids)
                        ]
                    }

                    for line in self.invoice_line_ids:
                        # Fetch the available quantity from the stock quant model
                        available_quants = self.env['stock.quant'].search([
                            ('product_id', '=', line.product_id.id),
                            ('location_id.usage', '=', 'internal')
                        ])
                        available_qty = sum(quant.quantity for quant in available_quants)

                        remaining_qty = available_qty + line.quantity

                    payload_stock_master = {
                        "tpin": company.tpin,
                        "bhfId": company.bhf_id,
                        "regrId": current_user.id,
                        "regrNm": current_user.name,
                        "modrNm": current_user.name,
                        "modrId": current_user.id,
                        "stockItemList": [
                            {
                                "itemCd": line.product_id.product_tmpl_id.item_Cd,
                                "rsdQty": remaining_qty
                            }
                        ]
                    }

                    _logger.info(f'Payload for stockMaster/saveStockMaster: {payload_stock_master}')
                    print(f'Payload for stockMaster/saveStockMaster: {payload_stock_items}')

                    result_msg_stock_items = self._post_to_api(config_settings.stock_master_endpoint,
                                                               payload_stock_items, "Stock items update")
                    result_msg_stock_master = self._post_to_api(config_settings.stock_master_endpoint,
                                                                payload_stock_master, "Stock master update")

                    # Post the resultMsg to the chatter
                    try:
                        _logger.info(
                            f'Attempting to post message for return of product: {product.display_name} on stock.picking')
                        picking.message_post(
                            body='Return quantity of product {} has been updated to {}. Endpoint responses: Stock items - {}, Stock master - {}'.format(
                                product.display_name,
                                -return_qty,
                                result_msg_stock_items,
                                result_msg_stock_master
                            ),
                            subtype_id=self.env.ref('mail.mt_note').id
                        )
                        _logger.info(
                            f'Message successfully posted for return of product: {product.display_name} on stock.picking')
                    except Exception as e:
                        _logger.error(
                            f'Failed to post message for return of product: {product.display_name} on stock.picking: {str(e)}')
                        print(
                            f'Failed to post message for return of product: {product.display_name} on stock.picking: {str(e)}')

            else:
                _logger.info(f'Skipping return for picking with type: {picking.picking_type_id.code}')
                print(f'Skipping return for picking with type: {picking.picking_type_id.code}')

    def _post_to_api(self, url, payload, success_message_prefix):
        print('Payload being sent:', json.dumps(payload, indent=4))
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
