# -*- coding: utf-8 -*-
{
    'name': "Angkort E-menu",

    'summary': "Short (1 phrase/line) summary of the module's purpose test",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['web', 'sale_management', 'html_editor', "contacts", 'hr', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_partner_views.xml',
        'views/angkort_shop_bank_views.xml',

        'views/product_template_views.xml',
        "views/product_category_views.xml",
        "views/product_attribute_views.xml",

        'views/menu_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

