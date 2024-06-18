from odoo import models, api
import logging
import requests

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        # Debugging: Log and print entering the method
        _logger.info('Entering button_validate method.')
        print('Entering button_validate method.')

        res = super(StockPicking, self).button_validate()

        for picking in self:
            # Debugging: Log and print picking type
            _logger.info(f'Processing picking with type: {picking.picking_type_id.code}')
            print(f'Processing picking with type: {picking.picking_type_id.code}')

            # Handle both incoming and outgoing pickings
            moves = picking.move_ids_without_package

            for move in moves:
                # Debugging: Log and print move details
                _logger.info(f'Processing move for product: {move.product_id.display_name}')
                print(f'Processing move for product: {move.product_id.display_name}')

                # Sample payload, you can customize it as per your needs
                payload = {
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
                    response = requests.post("http://localhost:8085/trnsPurchase/savePurchase", json=payload)
                    response.raise_for_status()
                    result_msg = response.json().get('resultMsg', 'No result message returned')

                    # Post the result message to the chatter
                    picking.message_post(
                        body="API Response Item Purchase: %s, \nProduct Name: %s" % (result_msg, move.product_id.display_name),
                        subtype_id=self.env.ref('mail.mt_note').id
                    )

                    _logger.info(f'API Response: {result_msg}')
                    print(f'API Response: {result_msg}')
                except requests.exceptions.RequestException as e:
                    _logger.error(f'API request failed: {e}')
                    print(f'API request failed: {e}')

                # Debugging: Confirm message was posted
                _logger.info(f'Message posted for product: {move.product_id.display_name}')
                print(f'Message posted for product: {move.product_id.display_name}')

            _logger.info(f'Skipping picking with type: {picking.picking_type_id.code}')
            print(f'Skipping picking with type: {picking.picking_type_id.code}')

        # Debugging: Log and print exiting the method
        _logger.info('Exiting button_validate method.')
        print('Exiting button_validate method.')

        return res
