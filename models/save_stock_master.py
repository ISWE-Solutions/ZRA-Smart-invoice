import requests
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class StockChangeProductQty(models.TransientModel):
    _inherit = 'stock.change.product.qty'

    def change_product_qty(self):
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
            payload = {
                "tpin": "1018798746",
                "bhfId": "000",
                "regrId": "Admin",
                "regrNm": "Admin",
                "modrNm": "Admin",
                "modrId": "Admin",
                "stockItemList": [
                    {
                        "itemCd": product.default_code or product.id,
                        "rsdQty": new_qty
                    }
                ]
            }

            try:
                # Make the POST request to the given endpoint
                response = requests.post('http://localhost:8085/stockMaster/saveStockMaster', json=payload)
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

    def create_returns(self):
        _logger.info('Entering create_returns method.')
        print('Entering create_returns method.')

        result = super(StockPickingReturn, self).create_returns()
        self._process_return_moves()

        _logger.info('Exiting create_returns method.')
        print('Exiting create_returns method.')

        return result

    def _process_return_moves(self):
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
                    payload_stock_items = {
                        "tpin": "1018798746",
                        "bhfId": "000",
                        "sarNo": 1,
                        "orgSarNo": 0,
                        "regTyCd": "M",
                        "custTpin": None,
                        "custNm": None,
                        "custBhfId": "000",
                        "sarTyCd": "13",
                        "ocrnDt": "20200126",
                        "totItemCnt": 2,
                        "totTaxblAmt": 70000,
                        "totTaxAmt": 12000,
                        "totAmt": 70000,
                        "remark": None,
                        "regrId": "Admin",
                        "regrNm": "Admin",
                        "modrNm": "Admin",
                        "modrId": "Admin",
                        "itemList": [
                            {
                                "itemSeq": 1,
                                "itemCd": "RW1NTXU0000006",
                                "itemClsCd": "5059690800",
                                "itemNm": "AMAZI Rwenzoli",
                                "bcd": None,
                                "pkgUnitCd": "NT",
                                "pkg": 10,
                                "qtyUnitCd": "U",
                                "qty": 10,
                                "itemExprDt": None,
                                "prc": 3500,
                                "splyAmt": 35000,
                                "totDcAmt": 0,
                                "taxblAmt": 35000,
                                "vatCatCd": "A",
                                "iplCatCd": "IPL1",
                                "tlCatCd": "TL",
                                "exciseTxCatCd": "EXEEG",
                                "vatAmt": 30508,
                                "iplAmt": 30508,
                                "tlAmt": 30508,
                                "exciseTxAmt": 30508,
                                "taxAmt": 6000,
                                "totAmt": 35000
                            },
                            {
                                "itemSeq": 2,
                                "itemCd": "RW2TYXLTR0000001",
                                "itemClsCd": "5059690800",
                                "itemNm": "MAZUT",
                                "bcd": None,
                                "pkgUnitCd": "NT",
                                "pkg": 10,
                                "qtyUnitCd": "U",
                                "qty": 10,
                                "itemExprDt": None,
                                "prc": 3500,
                                "splyAmt": 35000,
                                "totDcAmt": 0,
                                "taxblAmt": 35000,
                                "vatCatCd": "A",
                                "iplCatCd": "IPL1",
                                "tlCatCd": "TL",
                                "exciseTxCatCd": "EXEEG",
                                "vatAmt": 30508,
                                "iplAmt": 30508,
                                "tlAmt": 30508,
                                "exciseTxAmt": 30508,
                                "totAmt": 35000
                            }
                        ]
                    }

                    payload_stock_master = {
                        "tpin": "1018798746",
                        "bhfId": "000",
                        "regrId": "Admin",
                        "regrNm": "Admin",
                        "modrNm": "Admin",
                        "modrId": "Admin",
                        "stockItemList": [
                            {
                                "itemCd": product.default_code or product.id,
                                "rsdQty": -return_qty  # Decrease the quantity
                            }
                        ]
                    }

                    result_msg_stock_items = self._post_to_api('http://localhost:8085/stock/saveStockItems',
                                                               payload_stock_items, "Stock items update")
                    result_msg_stock_master = self._post_to_api('http://localhost:8085/stockMaster/saveStockMaster',
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
