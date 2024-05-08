# -*- coding: utf-8 -*-
{
    'name': "Pradowansa Custom Integration & Field",

    'summary': """
        This module is belong to PT. Pradowansa Sukses Lestari""",

    'description': """
        This is VIT Odoo Customization Field Module
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'module_type': 'official',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','account', 'purchase', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views_sale_order.xml',
        'views/views_account_move.xml',
        'views/views_stock_picking.xml',
        'views/views_account_payment_register.xml',
        'views/views_account_payment.xml',
        'views/views_purchase_order.xml',
        'views/views_res_partner.xml',
        'views/views_log_note_error.xml',
        'views/views_special_sync.xml',
        'views/views_account_account.xml',
    ],
}
