from odoo import models, api
import requests
import logging

_logger = logging.getLogger(__name__)

class QuantityUnitCode(models.AbstractModel):
    _name = 'quantity.data'
    _description = 'Fetch Quantity data from ZRA Endpoint'

    @api.model
    def fetch_quantity_data(self):
        url = 'http://localhost:8085/code/selectCodes'
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "lastReqDt": "20180520000000"
        }
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json().get('data', {}).get('clsList', [])
            quantity_options = []
            for cls_item in data:
                if cls_item['cdCls'] == '10':
                    for item in cls_item.get('dtlList', []):
                        quantity_options.append((item['cdNm'], {'quantity_unit_cd': item['cd']}))
                        # _logger.info('Fetched quantity unit: %s', item)
            return quantity_options

        except requests.exceptions.RequestException as e:
            _logger.error('Failed to fetch quantity data: %s', e)
            return []