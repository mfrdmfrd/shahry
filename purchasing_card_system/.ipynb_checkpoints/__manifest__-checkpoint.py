# -*- coding: utf-8 -*-
{
    'name': "Purchasing Card System",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hatem Mostafa",
    'website': "https://www.linkedin.com/in/hatem-mostafa-a6267b1a9/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/contract.xml',
        'views/card_purchase.xml',
        'views/partner.xml',
        'views/menuitems.xml',
    ],
}
