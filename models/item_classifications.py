from odoo import models, api
import logging
import json
import os
import requests

_logger = logging.getLogger(__name__)

class ZraItem(models.AbstractModel):
    _name = 'zra.item.save'
    _description = 'Zra Item Classification Saving Abstract Class'

    @api.model
    def fetch_classification_data(self):
        url = 'http://localhost:8085/itemClass/selectItemsClass'
        payload = {
            "tpin": "1018798746",
            "bhfId": "000",
            "lastReqDt": "20240123121449"
        }
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json().get('data', {}).get('itemClsList', [])
            classification_options = [
                (item['itemClsNm'], {
                    'itemClsCd': item['itemClsCd'],
                    'itemClsNm': item['itemClsNm'],
                    'itemClsLvl': item['itemClsLvl'],
                    'taxTyCd': item.get('taxTyCd', ''),
                    'mjrTgYn': item.get('mjrTgYn', ''),
                    'useYn': item['useYn']
                })
                for item in data if item['useYn'] == 'Y'
            ]
            return classification_options
        except requests.exceptions.RequestException as e:
            _logger.error('Failed to fetch classification data from ZRA: %s', e)
            return []
