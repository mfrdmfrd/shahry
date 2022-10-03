from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import json

from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    sub_type = fields.Selection([('csh', 'Cash'), ('pcsh', 'Petty Cash')], string='Sub Type')
    max_limit = fields.Float(string="Max Limit")
    current_Balance = fields.Float("Current Balance", compute='compute_petty_cash_balance')
    max_trans = fields.Float(compute="compute_petty_cash_balance")
    responsible = fields.Many2one("hr.employee", string="Employee")
    warning = fields.Boolean(default=False, compute="compute_petty_cash_balance")
    sequence_in_next = fields.Integer(string='In Next Number',
                                      compute='_compute_move_number_next',
                                      inverse='_inverse_move_number_next')
    sequence_in_code = fields.Char(string='Short Code (In)', size=8)
    sub_seq_in = fields.Many2one("ir.sequence", "Sequence In")
    sequence_out_next = fields.Integer(string='Out Next Number',
                                       compute='_compute_move_number_next',
                                       inverse='_inverse_move_number_next')
    sequence_out_code = fields.Char(string='Short Code (Out)', size=8)
    sub_seq_out = fields.Many2one("ir.sequence", "Sequence Out")

    @api.depends('sub_seq_in.use_date_range', 'sub_seq_in.number_next_actual')
    def _compute_move_number_next(self):
        for journal in self:
            if journal.sub_seq_in:
                sequence = journal.sub_seq_in._get_current_sequence()
                journal.sequence_in_next = sequence.number_next_actual
            else:
                journal.sequence_in_next = 1
            if journal.sub_seq_out:
                sequence = journal.sub_seq_out._get_current_sequence()
                journal.sequence_out_next = sequence.number_next_actual
            else:
                journal.sequence_out_next = 1

    def _inverse_move_number_next(self):
        for journal in self:
            if journal.sub_seq_in and journal.sequence_in_next:
                sequence = journal.sub_seq_in._get_current_sequence()
                sequence.sudo().number_next = journal.sequence_in_next
            if journal.sub_seq_out and journal.sequence_out_next:
                sequence = journal.sub_seq_out._get_current_sequence()
                sequence.sudo().number_next = journal.sequence_out_next

    @api.model
    def _create_in_sequence(self, vals):
        prefix = self._get_sequence_prefix(vals['sequence_in_code'])
        seq_name = vals['sequence_in_code']
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        seq_date_range = seq._get_current_sequence()
        seq_date_range.number_next = vals.get('sequence_in_next', 1)
        return seq

    @api.model
    def _create_out_sequence(self, vals):
        prefix = self._get_sequence_prefix(vals['sequence_out_code'])
        seq_name = vals['sequence_out_code']
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        seq_date_range = seq._get_current_sequence()
        seq_date_range.number_next = vals.get('sequence_out_next', 1)
        return seq

    def compute_petty_cash_balance(self):
        for rec in self:
            rec.warning = False
            if rec.sub_type == 'csh':
                move_lines = self.env['account.move.line'].search([('journal_id', '=', rec.id),
                                                                   ('move_id.state', '=', 'posted'),
                                                                   ('account_id', 'in', [rec.default_debit_account_id.id, rec.default_credit_account_id.id])])
                bal = sum(move_lines.mapped('balance'))
                rec.current_Balance = bal
                rec.max_trans = rec.max_limit - rec.current_Balance
                if rec.current_Balance > rec.max_limit:
                    rec.warning = True
            else:
                rec.current_Balance = rec.max_trans = 0



    # def get_journal_dashboard_datas(self):
    #     currency = self.currency_id or self.company_id.currency_id
    #     number_to_reconcile = number_to_check = last_balance = account_sum = 0
    #     title = ''
    #     number_draft = number_waiting = number_late = to_check_balance = 0
    #     sum_draft = sum_waiting = sum_late = 0.0
    #     if self.type in ['bank', 'cash']:
    #         last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc, id desc", limit=1)
    #         last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
    #         if self.sub_type == 'csh':
    #             last_balance = self.current_Balance
    #             account_sum = self.current_Balance
    #         #Get the number of items to reconcile for that bank journal
    #         self.env.cr.execute("""SELECT COUNT(DISTINCT(line.id))
    #                         FROM account_bank_statement_line AS line
    #                         LEFT JOIN account_bank_statement AS st
    #                         ON line.statement_id = st.id
    #                         WHERE st.journal_id IN %s AND st.state = 'open' AND line.amount != 0.0 AND line.account_id IS NULL
    #                         AND not exists (select 1 from account_move_line aml where aml.statement_line_id = line.id)
    #                     """, (tuple(self.ids),))
    #         number_to_reconcile = self.env.cr.fetchone()[0]
    #         to_check_ids = self.to_check_ids()
    #         number_to_check = len(to_check_ids)
    #         to_check_balance = sum([r.amount for r in to_check_ids])
    #         # optimization to read sum of balance from account_move_line
    #         account_ids = tuple(ac for ac in [self.default_debit_account_id.id, self.default_credit_account_id.id] if ac)
    #         if account_ids:
    #             amount_field = 'aml.balance' if (not self.currency_id or self.currency_id == self.company_id.currency_id) else 'aml.amount_currency'
    #             query = """SELECT sum(%s) FROM account_move_line aml
    #                        LEFT JOIN account_move move ON aml.move_id = move.id
    #                        WHERE aml.account_id in %%s
    #                        AND move.date <= %%s AND move.state = 'posted';""" % (amount_field,)
    #             self.env.cr.execute(query, (account_ids, fields.Date.context_today(self),))
    #             query_results = self.env.cr.dictfetchall()
    #             if query_results and query_results[0].get('sum') != None:
    #                 account_sum = query_results[0].get('sum')
    #                 if self.sub_type == 'csh':
    #                     last_balance = self.current_Balance
    #                     account_sum = self.current_Balance
    #     #TODO need to check if all invoices are in the same currency than the journal!!!!
    #     elif self.type in ['sale', 'purchase']:
    #         title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
    #         self.env['account.move'].flush(['amount_residual', 'currency_id', 'type', 'invoice_date', 'company_id', 'journal_id', 'date', 'state', 'invoice_payment_state'])
    #
    #         (query, query_args) = self._get_open_bills_to_pay_query()
    #         self.env.cr.execute(query, query_args)
    #         query_results_to_pay = self.env.cr.dictfetchall()
    #
    #         (query, query_args) = self._get_draft_bills_query()
    #         self.env.cr.execute(query, query_args)
    #         query_results_drafts = self.env.cr.dictfetchall()
    #
    #         today = fields.Date.today()
    #         query = '''
    #             SELECT
    #                 (CASE WHEN type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * amount_residual AS amount_total,
    #                 currency_id AS currency,
    #                 type,
    #                 invoice_date,
    #                 company_id
    #             FROM account_move move
    #             WHERE journal_id = %s
    #             AND date <= %s
    #             AND state = 'posted'
    #             AND invoice_payment_state = 'not_paid'
    #             AND type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt');
    #         '''
    #         self.env.cr.execute(query, (self.id, today))
    #         late_query_results = self.env.cr.dictfetchall()
    #         curr_cache = {}
    #         (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay, currency, curr_cache=curr_cache)
    #         (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts, currency, curr_cache=curr_cache)
    #         (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results, currency, curr_cache=curr_cache)
    #         read = self.env['account.move'].read_group([('journal_id', '=', self.id), ('to_check', '=', True)], ['amount_total'], 'journal_id', lazy=False)
    #         if read:
    #             number_to_check = read[0]['__count']
    #             to_check_balance = read[0]['amount_total']
    #     elif self.type == 'general':
    #         read = self.env['account.move'].read_group([('journal_id', '=', self.id), ('to_check', '=', True)], ['amount_total'], 'journal_id', lazy=False)
    #         if read:
    #             number_to_check = read[0]['__count']
    #             to_check_balance = read[0]['amount_total']
    #
    #     difference = currency.round(last_balance-account_sum) + 0.0
    #
    #     is_sample_data = self.kanban_dashboard_graph and any(data.get('is_sample_data', False) for data in json.loads(self.kanban_dashboard_graph))
    #
    #     return {
    #         'number_to_check': number_to_check,
    #         'to_check_balance': formatLang(self.env, to_check_balance, currency_obj=currency),
    #         'number_to_reconcile': number_to_reconcile,
    #         'account_balance': formatLang(self.env, currency.round(account_sum) + 0.0, currency_obj=currency),
    #         'last_balance': formatLang(self.env, currency.round(last_balance) + 0.0, currency_obj=currency),
    #         'difference': formatLang(self.env, difference, currency_obj=currency) if difference else False,
    #         'number_draft': number_draft,
    #         'number_waiting': number_waiting,
    #         'number_late': number_late,
    #         'sum_draft': formatLang(self.env, currency.round(sum_draft) + 0.0, currency_obj=currency),
    #         'sum_waiting': formatLang(self.env, currency.round(sum_waiting) + 0.0, currency_obj=currency),
    #         'sum_late': formatLang(self.env, currency.round(sum_late) + 0.0, currency_obj=currency),
    #         'currency_id': currency.id,
    #         'bank_statements_source': self.bank_statements_source,
    #         'title': title,
    #         'is_sample_data': is_sample_data,
    #     }
