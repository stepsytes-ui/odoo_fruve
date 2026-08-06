# -*- coding: utf-8 -*-
{
    'name': "maintenance_fruvemex",

    'summary': "Maintenance module",

    'description': """
Maintenance intern module for work orders for maintenance team.
    """,

    'author': "NeyiSoek",
    'website': "https://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '18.0.1.0.0',

    'depends': ['base', 'hr', 'overtime', 'mail'],
    'data': [
        'security/maintenance_security.xml',
        'security/ir.model.access.csv',
        'data/maintenance_sequence.xml',
        'views/maintenance_request_views.xml',
        'views/maintenance_menus.xml',
    ],
    'installable': True,
    'application': True,
}

