# -*- coding: utf-8 -*-
{
    'name': "zra smart invoice",

    'summary': "Intergration with Zra smart invoice system",

    'description': """
Intergration with Zra smart invoice system 
    """,

    'author': "Collins Matutu - Iswe solutions",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'bus', 'account', 'sale', 'mail', 'stock', 'web', 'mrp'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/import_view.xml',
        'views/purchase_views.xml',
        # 'views/smart_invoice_config.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/product_template_views.xml',
        'views/contacts.xml',
        'views/company.xml',
        'views/sales.xml',
        'wizards/account_debit_note_wizard.xml',
        'views/fetch_data_view.xml',
        'views/debit_note.xml',
        'views/debit_note_preview.xml',
        'views/invoice_reports.xml',
        'data/tax_types_data.xml',
        'views/smart_invoice_config.xml',
        'views/menu_view.xml',
        'report/custom_invoice_report.xml',
        'report/custom_invoice_report_action.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': "LGPL-3",
}
