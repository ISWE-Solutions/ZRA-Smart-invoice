from odoo import models, api
import logging
import json
import os

_logger = logging.getLogger(__name__)

class ZraItem(models.AbstractModel):
    _name = 'zra.item.save'
    _description = 'Zra Item Classification Saving Abstract Class'

    @api.model
    def fetch_classification_data(self):
        file_path = os.path.join(os.path.dirname(__file__), 'itemClass.json')
        try:
            with open(file_path, 'r') as json_file:
                data = json.load(json_file).get('data', {}).get('itemClsList', [])
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
        except Exception as e:
            _logger.error('Failed to read classification data from itemClass.json: %s', e)
            return []
