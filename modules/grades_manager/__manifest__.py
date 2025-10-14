# -*- coding: utf-8 -*-
{
    'name': "grades_manager",

    'summary': "Modulo del curso de Udemy para practicar",

    'description': """
Modulo del curso de Udemy para practicar
    """,

    'author': "DCG",
    'website': "https://www.dcg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/views.xml',
        'views/templates.xml',
        
    ],
    # only loaded in demonstration mode
    'demo': [],
    'license': 'LGPL-3',
    'installable': True,

    #Truen when the module is a application
    'application': False,
    'auto_install': False,
}

