# -*- coding: utf-8 -*-
{
    'name': "beacukai",

    'summary': """
        BeaCukai documents, BeaCukai reports""",

    'description': """
        
    """,

    'author': "Hendra Saputra - hendrasaputra0501@gmail.com",
    'website': "-",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Beacukai',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','account','master_data_custom'],

    # always loaded
    'data': [
        # 'security/beacukai_security.xml',
        # 'security/ir.model.access.csv',
        'views/beacukai_view.xml',
        'views/beacukai_line_view.xml',
        'views/wizard_beacukai_incoming_view.xml',
        'views/wizard_beacukai_outgoing_view.xml',
        'views/wizard_product_mutation_view.xml',
        'views/wizard_product_work_in_process_view.xml',
        'views/beacukai_state_view.xml',
        'views/menuitem.xml',
        # 'report/report_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}