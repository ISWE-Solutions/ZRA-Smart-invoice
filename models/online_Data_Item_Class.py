from odoo import models, api
import logging
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

    from odoo import models, api
    import logging
    import requests

    _logger = logging.getLogger(__name__)

    class ClassCodes(models.AbstractModel):
        _name = 'class.codes'
        _description = 'Zra Class Codes for multiple End points'

        # Class-level variable to store fetched country codes
        _country_codes = []

        @classmethod
        def fetch_class_codes(cls):
            # Check if country codes are already fetched and cached
            if cls._country_codes:
                return cls._country_codes

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
                response.raise_for_status()  # Raise an error for bad status codes

                data = response.json()
                _logger.debug("Response from API: %s", data)

                # Extract country codes from API response
                country_codes = [
                    (item['cd'], item['cdNm'])
                    for cls_item in data.get('data', {}).get('clsList', [])
                    if cls_item.get('cdCls') == '05'
                    for item in cls_item.get('dtlList', [])
                ]

                _logger.info("Fetched country codes: %s", country_codes)

                # Cache the fetched country codes
                cls._country_codes = country_codes

                return country_codes

            except requests.exceptions.HTTPError as http_err:
                _logger.error('HTTP error occurred: %s', http_err)
                return []
            except Exception as err:
                _logger.error('Other error occurred: %s', err)
                return []
