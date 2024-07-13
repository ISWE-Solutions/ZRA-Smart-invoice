from odoo import models, fields, api, _
import requests
import logging

_logger = logging.getLogger(__name__)


class CountryData(models.AbstractModel):
    _name = 'country.data'
    _description = 'Fetch Country Data from Endpoint'

    @api.model
    def fetch_country_data(self):
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
            country_options = [
                (item['cdNm'], {
                    'cd': item['cd']
                })
                for cls_item in data if cls_item['cdCls'] == '05'
                for item in cls_item.get('dtlList', [])
            ]
            return country_options

        except requests.exceptions.RequestException as e:
            _logger.error('Failed to fetch country data: %s', e)
            return []
