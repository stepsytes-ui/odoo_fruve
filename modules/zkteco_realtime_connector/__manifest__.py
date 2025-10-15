# -*- coding: utf-8 -*-
{
    'name': "zkteco_realtime_connector",

    'summary': "Aplicacion de prueba para obtener datos del checador",

    'description': """
Modulo para integración de ZKTeco en odoo
    """,

    'author': "NeyiSoek",
    'website': "https://www.Fruvemex.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '18.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'application': True,
    'license':'LGPL-3',
}

