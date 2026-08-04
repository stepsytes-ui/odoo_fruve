# -*- coding: utf-8 -*-
{
    'name': "customer_polair",

    'summary': "Modulo para editar diferentes modulos de Odoo deacuerdo a las necesidades de Polair",

    'description': """
Principalmente se modifico, Compras, Ventas, Contactos, Inventario y se creo un modelo nuevo para Ordenes de trabajo.
    """,

    'author': "NeyiSoek",
    'website': "https://www.Fruvemex.com",
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'hr', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/custom_tax_option_data.xml',
        'data/work_order_data.xml',
        'data/ir_cron_data.xml',
        'views/custom_tax_option_views.xml',
        'views/customers.xml',
        'views/sale_order_line_views.xml',
        'views/sale_order_report_views.xml',
        'views/work_order_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

