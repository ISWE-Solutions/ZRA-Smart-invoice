from odoo import models, api
import logging
import requests

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        _logger.info('Entering button_validate method.')
        print('Entering button_validate method.')

        res = super(StockPicking, self).button_validate()

        for picking in self:
            _logger.info(f'Processing picking with type: {picking.picking_type_id.code}')
            print(f'Processing picking with type: {picking.picking_type_id.code}')

            moves = picking.move_ids_without_package

            for move in moves:
                product = move.product_id
                new_qty = product.qty_available
                product_template = product.product_tmpl_id

                _logger.info(f'Processing move for product: {product.display_name}')
                print(f'Processing move for product: {product.display_name}')

                # Payload for the first API request
                payload_purchase = {
                    "tpin": "1018798746",
                    "bhfId": "000",
                    "invcNo": 9,
                    "orgInvcNo": 0,
                    "spplrTpin": "1000328006",
                    "spplrBhfId": "000",
                    "spplrNm": "Company 1234",
                    "spplrInvcNo": "88",
                    "regTyCd": "M",
                    "pchsTyCd": "N",
                    "rcptTyCd": "P",
                    "pmtTyCd": "01",
                    "pchsSttsCd": "02",
                    "cfmDt": "20240502210300",
                    "pchsDt": "20240502",
                    "wrhsDt": "",
                    "cnclReqDt": "",
                    "cnclDt": "",
                    "rfdDt": "",
                    "totItemCnt": 1,
                    "totTaxblAmt": 86.2069,
                    "totTaxAmt": 13.7931,
                    "totAmt": 100,
                    "remark": "Very yummy yummy",
                    "regrNm": "LUNGUJ",
                    "regrId": "LUNGUJ",
                    "modrNm": "LUNGUJ",
                    "modrId": "LUNGUJ",
                    "itemList": [
                        {
                            "itemSeq": 1,
                            "itemCd": "20044",
                            "itemClsCd": "5059690800",
                            "itemNm": "Chicken Wings",
                            "bcd": "",
                            "spplrItemClsCd": None,
                            "spplrItemCd": None,
                            "spplrItemNm": None,
                            "pkgUnitCd": "NT",
                            "pkg": 2,
                            "qtyUnitCd": "U",
                            "qty": 1,
                            "prc": 100,
                            "splyAmt": 100,
                            "dcRt": 0,
                            "dcAmt": 0,
                            "vatCatCd": "A",
                            "iplCatCd": None,
                            "tlCatCd": None,
                            "exciseTxCatCd": None,
                            "taxAmt": 0,
                            "taxblAmt": 0,
                            "totAmt": 100,
                            "itemExprDt": None
                        }
                    ]
                }

                try:
                    response = requests.post("http://localhost:8085/trnsPurchase/savePurchase", json=payload_purchase)
                    response.raise_for_status()
                    result_msg_purchase = response.json().get('resultMsg', 'No result message returned')

                    # Post the result message to the chatter
                    picking.message_post(
                        body="API Response Item Purchase: %s, \nProduct Name: %s" % (result_msg_purchase, move.product_id.display_name),
                        subtype_id=self.env.ref('mail.mt_note').id
                    )

                    _logger.info(f'API Purchase Response: {result_msg_purchase}')
                    print(f'API Purchase Response: {result_msg_purchase}')
                except requests.exceptions.RequestException as e:
                    _logger.error(f'API request failed: {e}')
                    print(f'API request failed: {e}')

                # Debugging: Confirm message was posted
                _logger.info(f'Message posted for product: {move.product_id.display_name}')
                print(f'Message posted for product: {move.product_id.display_name}')

                # Payload for the second API request (new endpoint)
                payload_new_endpoint = {
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

                try:
                    response = requests.post('http://localhost:8085/stock/saveStockItems', json=payload_new_endpoint)
                    response.raise_for_status()
                    result_msg_new_endpoint = response.json().get('resultMsg', 'No result message returned')

                    # Post the result message to the chatter
                    picking.message_post(
                        body="Save Stock API Response New Endpoint: %s, \nProduct Name: %s" % (result_msg_new_endpoint, move.product_id.display_name),
                        subtype_id=self.env.ref('mail.mt_note').id
                    )

                    _logger.info(f'API New Endpoint Response: {result_msg_new_endpoint}')
                    print(f' Save Stock Item API Endpoint Response: {result_msg_new_endpoint}')
                except requests.exceptions.RequestException as e:
                    _logger.error(f'API request failed: {e}')
                    print(f'API request failed: {e}')

                # Payload for the third API request
                payload_stock = {
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
                    response = requests.post('http://localhost:8085/stockMaster/saveStockMaster', json=payload_stock)
                    response.raise_for_status()
                    result_msg_stock = response.json().get('resultMsg', 'No result message received')
                    _logger.info(f'Endpoint response: {result_msg_stock}')
                    print(f'Stock Master Endpoint response: {result_msg_stock}')
                except requests.exceptions.RequestException as e:
                    result_msg_stock = str(e)
                    _logger.error(f'Error during POST request: {result_msg_stock}')
                    print(f'Error during POST request: {result_msg_stock}')

                # Post the resultMsg to the chatter
                picking.message_post(
                    body='Quantity of product {} has been updated to {}. Endpoint response: {}'.format(product.display_name, new_qty, result_msg_stock),
                    subtype_id=self.env.ref('mail.mt_note').id
                )

                _logger.info(f'Message posted for product: {product.display_name} on stock.picking')
                print(f'Message posted for product: {product.display_name} on stock.picking')

            _logger.info(f'Skipping picking with type: {picking.picking_type_id.code}')
            print(f'Skipping picking with type: {picking.picking_type_id.code}')

        _logger.info('Exiting button_validate method.')
        print('Exiting button_validate method.')

        return res
