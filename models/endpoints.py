from odoo import models, fields, api, _


class Endpoints(models.Model):
    _name = 'endpoints'
    _description = 'Zra VSDC endpoint location'

    fetch_data_button = fields.Boolean(string="Fetch Data")

    classification_endpoint = fields.Char(string='classification  ZRA Endpoint',
                                          default="http://localhost:8085/itemClass/selectItemsClass")
    class_codes_endpoint = fields.Char(string='class codes ZRA Endpoint',
                                       default="http://localhost:8085/code/selectCodes")
    sales_endpoint = fields.Char(string='Sales ZRA Endpoint', default="http://localhost:8085/trnsSales/saveSales")
    purchase_endpoint = fields.Char(string='Purchase ZRA Endpoint',
                                    default="http://localhost:8085/trnsPurchase/savePurchase")
    purchase_si_endpoint = fields.Char(string='Purchase SI ZRA Endpoint',
                                       default="http://localhost:8085/trnsPurchase/selectTrnsPurchaseSales")
    inventory_endpoint = fields.Char(string='Inventory ZRA Endpoint', default="http://localhost:8085/items/saveItem")
    import_endpoint = fields.Char(string='Import ZRA Endpoint',
                                  default="http://localhost:8085/imports/selectImportItems")
    stock_io_endpoint = fields.Char(string='Stock I/O ZRA Endpoint',
                                    default="http://localhost:8085/stock/saveStockItems")
    stock_master_endpoint = fields.Char(string='Stock Master ZRA Endpoint',
                                        default="http://localhost:8085/stockMaster/saveStockMaster")

    # Newly added fields
    import_update_endpoint = fields.Char(string='Import Update ZRA Endpoint',
                                         default="http://localhost:8085/imports/updateImportItems")
    inventory_update_endpoint = fields.Char(string='Inventory Update ZRA Endpoint',
                                            default="http://localhost:8085/items/updateItem")

    @api.model
    def create(self, vals):
        # Unlink all existing records
        existing_records = self.search([])
        if existing_records:
            existing_records.unlink()

        # Proceed with the creation of the new record
        return super(Endpoints, self).create(vals)

    @api.model
    def write(self, vals):
        # Unlink all existing records before updating
        existing_records = self.search([])
        if existing_records:
            existing_records.unlink()

        # Proceed with updating the current record
        return super(Endpoints, self).write(vals)
