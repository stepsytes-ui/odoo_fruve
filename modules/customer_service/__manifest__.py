# -*- coding: utf-8 -*-
{
    'name': "customer_service",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "NeyiSoek",
    'website': "https://www.Fruvemex.com",
    'category': 'Manufacturing',
    'version': '18.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'Warehouse_Management'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sequence.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}


