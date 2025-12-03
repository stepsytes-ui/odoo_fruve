# -*- coding: utf-8 -*-
{
    'name': "employee_modifications",

    'summary': "Fruvemex requests for employee's module",

    'description': """
Fruvemex requests for employee's module
    """,

    'author': "NeyiSoek",
    'website': "https://fruvemex.com/es/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '18.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance', 'web','zkteco_realtime_connector',],

        # always loaded
    'data': [
            'security/ir.model.access.csv',
            'views/employee_expedient.xml', 
            'views/employee_menus.xml',
            'views/employee_disciplinary.xml', 
            'wizard/employee_expedient_wizard_views.xml',
        ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

