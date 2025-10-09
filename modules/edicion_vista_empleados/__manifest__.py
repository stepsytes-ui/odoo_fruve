# -*- coding: utf-8 -*-
{
    'name': "Edicion Vista Empleados",

    'summary': "Upgrade to employee's module",

    'description': """
    Modulo para editar vista de empleados basado en los requerimientos de la empresa
    """,

    'author': "NeyiSoek",
    'website': "N/A",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'license': 'LGPL-3',
}

