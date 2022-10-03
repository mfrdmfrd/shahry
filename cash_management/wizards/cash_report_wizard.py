from odoo import api, fields, models, _
from datetime import datetime, timedelta
import calendar


class CashReportWizard(models.TransientModel):
    _name = 'cash.report.wizard'
    _description = 'Cash Report Wizard'

    date_from = fields.Date()
    date_to = fields.Date()
    journal_id = fields.Many2one("account.journal", domain="[('sub_type', '=', 'csh')]")

    def get_document(self, id):
        line = self.env["account.move.line"].search([("id", "=", id)], limit=1)
        doc = ''
        if line.payment_id:
            doc = line.payment_id.check_number
        else:
            ex_id = line.move_id.id
            doc = self.env['direct.expense'].search([('move_id', '=', ex_id)], limit=1).ref
        return doc

    def get_balance_line(self, id, debit, credit, date, move_id, journal):
        c = 0
        d = 0
        acc = 34
        lines = self.env['account.move.line'].search([
            ('move_id.state', '=', 'posted'),
            ('date', '<', date),
            ('account_id', '=', acc)])
        cur_lines = self.env['account.move.line'].search([('move_id.state', '=', 'posted'),
                                                          ('move_id.id', '<', move_id),
                                                          ('date', '=', date),
                                                          ('account_id', '=', acc)])
        bal = debit - credit
        if lines:
            d = sum(lines.mapped('debit'))
            c = sum(lines.mapped('credit'))
        if cur_lines:
            d += sum(cur_lines.mapped('debit'))
            c += sum(cur_lines.mapped('credit'))
        bal += d - c
        return bal

    def print_report(self):
        results = []
        results_total = []
        dt = datetime.today()
        fr_date = datetime(dt.year, 1, 1).date()
        journal = self.journal_id
        account_journal = self.journal_id.default_debit_account_id.name
        account_code = self.journal_id.default_debit_account_id.code
        date_from = self.date_from or fr_date
        date_to = self.date_to or fields.Date.today()
        responsible = journal.responsible.name
        self._cr.execute(
            """
                    SELECT
                        aml.id,
                        aml.id as move_line_id,
                        am.date as date,
                        am.id as move_id,
                        am.id as move_number,
                        am.name as move_name,
                        aml.name as name,
                        am.partner_id as partner_id,
                        aml.account_id as account_id,
                        aml.journal_id as journal_id,
                        aml.debit as debit,
                        aml.credit as credit,
                        aml.analytic_account_id as analytic_account_id
                        FROM account_move am join account_move_line aml on am.id = aml.move_id
                        JOIN account_journal AS aj ON aml.account_id = aj.default_debit_account_id
                        WHERE am.state = 'posted'
                        AND aml.journal_id = %s
                        AND am.date >= %s
                        AND am.date <= %s
                        ORDER BY aml.date asc, am.id                       
                    """, [journal.id, date_from, date_to]
        )
        moves = self._cr.dictfetchall()

        chk = 0
        total_debit = 0
        total_credit = 0
        total_balance = 0
        for line in moves:
            if chk != line["id"]:
                chk = line["id"]
                bal = self.get_balance_line(line["id"], line["debit"], line["credit"], line["date"],
                                            line["move_number"], journal)
                name = self.get_document(line["id"])
                account = self.env['account.move.line'].search([('id', '=', line["id"])], limit=1)
                account_lines = self.env['account.move.line'].search([('move_id', '=', account.move_id.id),
                                                                      ('id', '!=', line["id"])], limit=1)
                rec = {
                    'date': line["date"],
                    'debit': round(line["debit"], 2),
                    'credit': round(line["credit"], 2),
                    'bal': round(bal, 2),
                    'name': name,
                    'move_id': line["move_name"],
                    'analytic_account_id': account_lines.analytic_account_id.name,
                    'account_id': account_lines.account_id.name
                }
                total_debit += line["debit"]
                total_credit += line["credit"]
                total_balance = bal
                results.append(rec)
        results_total.append({
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance
        })
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': date_from,
                'date_to': date_to,
                'journal_id': journal.id,
                'journal_name': journal.name,
                'account': account_journal,
                'account_code': account_code,
                'currency': journal.currency_id.name,
                'lines': results,
                'results_total': results_total
            },
        }
        return self.env.ref('cash_management.cash_report').report_action(self, data=data)
