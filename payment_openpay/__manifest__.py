# -*- coding: utf-8 -*-
{
    'name': "payment_openpay",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'version': '0.1',
    'contributors':'itobetter@gmail.com',
    # any module necessary for this one to work correctly
    'depends': ['website_sale','account_payment'],
    'external_dependencies' : {
        'python' : ['openpay'],
    },
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
