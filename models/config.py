from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fetch_data_button = fields.Boolean(string="Fetch Data")

    endpoint_hit_counts = {
        'endpoint_1': 0,
        'endpoint_2': 0
    }

    def fetch_data(self):
        self.env['zra.item.data'].fetch_and_store_classification_data()
        common_data = self.env['code.data'].fetch_common_code_data()
        self.env['quantity.unit.data'].store_quantity_data(common_data)
        self.env['packaging.unit.data'].store_packaging_data(common_data)
        self.env['country.data'].store_country_data(common_data)
        _logger.info("Data fetched and stored successfully.")

        print(f"Endpoint 1 hit {self.endpoint_hit_counts['endpoint_1']} time(s)")
        print(f"Endpoint 2 hit {self.endpoint_hit_counts['endpoint_2']} time(s)")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Data fetched and stored successfully.',
                'type': 'success',
                'sticky': False,
            }
        }



