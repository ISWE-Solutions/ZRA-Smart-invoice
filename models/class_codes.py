from odoo import models, api
import logging
import requests
import json
import os
import time
from datetime import datetime, timedelta
import threading

_logger = logging.getLogger(__name__)


class ClassCodes(models.AbstractModel):
    _name = 'class.codes'
    _description = 'Zra Class Codes for multiple End points'

    _country_codes = []

    @classmethod
    def fetch_class_codes(cls):
        file_path = 'class_codes.json'

        # Check if the file exists and is less than 24 hours old
        if os.path.exists(file_path):
            last_modified_time = os.path.getmtime(file_path)
            if time.time() - last_modified_time < 24 * 3600:
                # Load data from the file
                _logger.info("Loading country codes from file.")
                with open(file_path, 'r') as f:
                    cls._country_codes = json.load(f)
                return cls._country_codes

        # Fetch data from the API
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

            data = response.json()
            _logger.debug("Response from API: %s", data)

            country_codes = [
                (item['cd'], item['cdNm'])
                for cls_item in data.get('data', {}).get('clsList', [])
                if cls_item.get('cdCls') == '05'
                for item in cls_item.get('dtlList', [])
            ]

            _logger.info("Fetched country codes: %s", country_codes)
            cls._country_codes = country_codes

            # Save to file
            cls.save_to_file(country_codes)

            return country_codes

        except requests.exceptions.HTTPError as http_err:
            _logger.error('HTTP error occurred: %s', http_err)
            return []
        except Exception as err:
            _logger.error('Other error occurred: %s', err)
            return []

    @classmethod
    def save_to_file(cls, data):
        file_path = 'class_codes.json'
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            _logger.info("Data saved to %s", file_path)
        except IOError as e:
            _logger.error("Unable to save data to file: %s", e)

    @classmethod
    def schedule_fetch(cls, interval=86400):
        while True:
            _logger.info("Fetching class codes...")
            cls.fetch_class_codes()
            _logger.info("Next fetch scheduled in %s seconds.", interval)
            time.sleep(interval)


# Scheduling the fetch operation every 24 hours (86400 seconds)
thread = threading.Thread(target=ClassCodes.schedule_fetch)
thread.daemon = True  # Ensure it exits when the main program exits
thread.start()
