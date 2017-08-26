# -*- coding: utf-8 -*-
{
    'name': "master_data_custom",

    'summary': """
        Products, Customers, Suppliers""",

    'description': """
        
    """,

    'author': "Hendra Saputra - hendrasaputra0501@gmail.com",
    'website': "-",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','stock'],

    # always loaded
    'data': [
        'security/master_data_custom_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}