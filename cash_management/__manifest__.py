# -*- coding: utf-8 -*-
{
    'name': "cash_management",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Raqmi",
    'website': "https://raqmisolutions.com",
    'category': 'Accounting/Accounting',
    'version': '0.1',
    'depends': ['base', 'web', 'account', 'date_range', 'hr', 'account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/account_account.xml',
        'views/direct_expenses.xml',
        'views/account_journal.xml',
        'views/account_move.xml',

        'data/paper_format.xml',
        'reports/cash_out.xml',
        'reports/cash_report.xml',
        'wizards/cash_report_wizard.xml'
    ]
}
