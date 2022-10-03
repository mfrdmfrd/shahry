
from odoo import api, fields, models, _, tools


class CashReport(models.AbstractModel):
    _name = 'report.cash_management.cash_report_template'
    _description = "print cash report"

    def _get_report_values(self, docids, data=None):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        journal_id = data['form']['journal_id']
        journal_name = data['form']['journal_name']
        account = data['form']['account']
        account_code = data['form']['account_code']
        currency = data['form']['currency']
        results = data['form']['lines']
        results_total = data['form']['results_total']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'date_to': date_to,
                'date_from': date_from,
                'journal_name': journal_name,
                'account': account,
                'account_code': account_code,
                'currency': currency,
                'docs': results,
                'docs_totals': results_total
            }
