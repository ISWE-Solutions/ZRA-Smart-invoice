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
                body='Quantity of product {} has been updated to {}. Endpoint response: {}'.format(product.display_name, new_qty, result_msg),
                subtype_id=self.env.ref('mail.mt_note').id
            )

            _logger.info(f'Message posted for product: {product.display_name} on product.template')
            print(f'Message posted for product: {product.display_name} on product.template')

        _logger.info('Exiting change_product_qty method.')
        print('Exiting change_product_qty method.')

        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        _logger.info('Entering button_validate method.')
        print('Entering button_validate method.')

        res = super(StockPicking, self).button_validate()

        for picking in self:
            _logger.info(f'Processing picking with type: {picking.picking_type_id.code}')
            print(f'Processing picking with type: {picking.picking_type_id.code}')

            if picking.picking_type_id.code in ['incoming', 'outgoing']:
                moves = picking.move_ids_without_package

                for move in moves:
                    product = move.product_id
                    new_qty = product.qty_available
                    product_template = product.product_tmpl_id

                    _logger.info(f'Processing move for product: {product.display_name}')
                    print(f'Processing move for product: {product.display_name}')

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
                    picking.message_post(
                        body='Quantity of product {} has been updated to {}. Endpoint response: {}'.format(product.display_name, new_qty, result_msg),
                        subtype_id=self.env.ref('mail.mt_note').id
                    )

                    _logger.info(f'Message posted for product: {product.display_name} on stock.picking')
                    print(f'Message posted for product: {product.display_name} on stock.picking')

            else:
                _logger.info(f'Skipping picking with type: {picking.picking_type_id.code}')
                print(f'Skipping picking with type: {picking.picking_type_id.code}')

        _logger.info('Exiting button_validate method.')
        print('Exiting button_validate method.')

        return res


class StockPickingReturn(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        _logger.info('Entering create_returns method.')
        print('Entering create_returns method.')

        result = super(StockPickingReturn, self).create_returns()

        for picking in self.env['stock.picking'].browse(self._context.get('active_ids', [])):
            _logger.info(f'Processing return for picking with type: {picking.picking_type_id.code}')
            print(f'Processing return for picking with type: {picking.picking_type_id.code}')

            # Ensure handling returns for relevant picking types
            if picking.picking_type_id.code in ['incoming', 'outgoing']:
                moves = picking.move_ids_without_package

                for move in moves:
                    product = move.product_id
                    return_qty = move.product_qty  # Quantity being returned
                    product_template = product.product_tmpl_id

                    _logger.info(f'Processing return move for product: {product.display_name}')
                    print(f'Processing return move for product: {product.display_name}')

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
                                "rsdQty": -return_qty  # Decrease the quantity
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
                    try:
                        _logger.info(f'Attempting to post message for return of product: {product.display_name} on stock.picking')
                        picking.message_post(
                            body='Return quantity of product {} has been updated to {}. Endpoint response: {}'.format(product.display_name, -return_qty, result_msg),
                            subtype_id=self.env.ref('mail.mt_note').id
                        )
                        _logger.info(f'Message successfully posted for return of product: {product.display_name} on stock.picking')
                    except Exception as e:
                        _logger.error(f'Failed to post message for return of product: {product.display_name} on stock.picking: {str(e)}')
                        print(f'Failed to post message for return of product: {product.display_name} on stock.picking: {str(e)}')

            else:
                _logger.info(f'Skipping return for picking with type: {picking.picking_type_id.code}')
                print(f'Skipping return for picking with type: {picking.picking_type_id.code}')

        _logger.info('Exiting create_returns method.')
        print('Exiting create_returns method.')

        return result
