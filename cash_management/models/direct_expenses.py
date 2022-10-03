import json
from datetime import datetime, timedelta
from ..models.money_to_text_ar import amount_to_text_arabic
from babel.dates import format_datetime, format_date
from odoo import models, api, _, fields, tools
from odoo.osv import expression
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, safe_eval
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang
import random
from odoo.exceptions import AccessError, except_orm, ValidationError, UserError

import ast


class CustomCash(models.Model):
    _name = 'direct.expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference Number', index=True, readonly=True, copy=False, default=lambda self: '/')
    ref = fields.Char()
    date = fields.Date(required=True, default=datetime.today(), tracking=True, track_visibility="onchange")
    cash_id = fields.Many2one("account.journal", string="Journal", domain="[('type', 'in', ('cash', 'bank'))]",
                              required=True, default=datetime.today(), tracking=True, track_visibility="onchange")
    journal_type = fields.Selection(related="cash_id.type")
    type = fields.Selection([('in_invoice', 'In'), ('out_invoice', 'Out')], default="out_invoice", required=True, tracking=True,
                            track_visibility="onchange")
    move_id = fields.Many2one("account.move", string="Journal Entry", required=False,
                              domain="[('type', 'not in', ('out_invoice','in_invoice'))]", readonly=True
                              , tracking=True, track_visibility="onchange")
    line_ids = fields.One2many(comodel_name="direct.expense.lines", inverse_name="direct_expense_id",
                               string="Lines", required=False)
    move_line_ids = fields.One2many(related='move_id.line_ids')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('posted', 'Posted'),
        ('cancel', "Cancelled"),
    ], 'Status', default="draft", readonly=True, tracking=True, track_visibility="onchange")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
                                  states={'draft': [('readonly', False)]},
                                  string='Currency')
    amount_untaxed = fields.Monetary(store=True, readonly=True, tracking=True, compute='_compute_amount')
    amount_total = fields.Monetary(store=True, readonly=True, compute='_compute_amount')
    total_tax = fields.Monetary(store=True, readonly=True, compute='_compute_amount')
    account_move_line = fields.One2many(related="move_id.line_ids")
    posted_before = fields.Boolean(default=False)
    description = fields.Text("Description")
    move_notes = fields.Text("Description")
    amount_text = fields.Char(compute='_compute_amount_in_word')
    manual_currency_exchange_rate = fields.Float(string='Exchange Rate')
    currency_type = fields.Char()
    income_type = fields.Char()
    income_serial = fields.Char()
    income_department = fields.Char()

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal = vals.get('cash_id')
            serial = self.env['account.journal'].search([('id', '=', journal)], limit=1)
            if vals.get('type', 'out_invoice') == 'out_invoice':
                vals['name'] = self.env['ir.sequence'].next_by_code(serial.sub_seq_in.code)
            if vals.get('type', 'in_invoice') == 'in_invoice':
                vals['name'] = self.env['ir.sequence'].next_by_code(serial.sub_seq_out.code)
        result = super(CustomCash, self).create(vals)
        return result

    def _compute_amount_in_word(self):
        for rec in self:
            rec.amount_text = str(rec.amount_text_arabic(rec.amount_total))

    def amount_text_arabic(self, amount_total):
        return amount_to_text_arabic(amount_total, self.currency_id.name)

    @api.onchange('cash_id')
    def onchange_cash_id(self):
        for rec in self:
            rec.currency_id = rec.cash_id.currency_id if rec.cash_id.currency_id else rec.company_id.currency_id
            if rec.cash_id.currency_id and rec.cash_id.currency_id.id != rec.company_id.currency_id.id:
                rec.manual_currency_exchange_rate = 1 / rec.currency_id.rate
                rec.currency_type = 'f'
            else:
                rec.manual_currency_exchange_rate = 1
                rec.currency_type = 'l'

    @api.depends('line_ids.amount', 'line_ids.amount_taxed')
    def _compute_amount(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped('amount'))
            rec.amount_total = sum(rec.line_ids.mapped('amount_taxed'))
            rec.total_tax = rec.amount_total - rec.amount_untaxed

    def _prepare_move_values(self):
        for rec in self:
            lines = [(5, 0, 0)]
            total = 0
            total_currency = 0
            for line in rec.line_ids:
                line_amount = line.amount
                amount_currency = False
                if rec.currency_id.id != self.company_id.currency_id.id:
                    if rec.type == 'out_invoice':
                        amount_currency = line.amount
                        line_amount = line.amount * rec.manual_currency_exchange_rate
                    if rec.type == 'in_invoice':
                        amount_currency = line.amount * -1
                        line_amount = line.amount * rec.manual_currency_exchange_rate
                    total_currency += amount_currency
                taxes = line.tax_id.with_context(round=True).compute_all(
                    line_amount, rec.currency_id, 1,
                    False)
                total += line_amount

                line_vals = {
                    'name': rec.ref,
                    'account_id': line.account_id.id,
                    'journal_id': rec.cash_id.id,
                    'date': rec.date,
                    'partner_id': line.partner_id.id,
                    'debit': line_amount if rec.type == 'out_invoice' else 0,
                    'credit': line_amount if rec.type == 'in_invoice' else 0,
                    'exclude_from_invoice_tab': True,
                    # 'direct_expense_id': rec.sub_code,
                    'analytic_account_id': line.analytic_account_id.id,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'amount_currency': amount_currency,
                    'currency_id': rec.currency_id.id if rec.currency_id.id != self.company_id.currency_id.id else False
                }
                lines.append((0, 0, line_vals))
                for tax in taxes['taxes']:
                    if tax['tax_repartition_line_id']:
                        rep_ln = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
                        base_amount = self.env['account.move']._get_base_amount_to_display(tax['base'], rep_ln)
                    else:
                        base_amount = None
                    amount = tax['amount']
                    if rec.type == 'out_invoice':
                        total += amount
                    else:
                        total -= amount
                    total_currency += amount / rec.manual_currency_exchange_rate if rec.currency_id.id != self.company_id.currency_id.id else 0
                    tax_cur = amount / rec.manual_currency_exchange_rate if rec.currency_id.id != self.company_id.currency_id.id else False

                    move_line_tax_values = {
                        'name': tax['name'],
                        'quantity': 1,
                        'debit': amount if amount > 0 else 0,
                        'credit': -amount if amount < 0 else 0,
                        'account_id': tax['account_id'],
                        'tax_repartition_line_id': tax['tax_repartition_line_id'],
                        'tax_ids': tax['tax_ids'],
                        'tax_base_amount': base_amount,
                        # 'direct_expense_id': rec.sub_code,
                        'analytic_account_id': line.analytic_account_id.id,
                        'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                        'amount_currency': tax_cur,
#                         'partner_id': line.partner_id.id,
                        'currency_id': rec.currency_id.id if rec.currency_id.id != self.company_id.currency_id.id else False
                    }
                    lines.append((0, 0, move_line_tax_values))
            if rec.currency_id.id != self.company_id.currency_id.id:
                if rec.type == 'out_invoice':
                    if total_currency > 0:
                        total_currency = total_currency * -1
                if rec.type == 'in_invoice':
                    if total_currency < 0:
                        total_currency = total_currency * -1
            othr_val = {
                'name': rec.ref,
                'account_id': rec.cash_id.default_account_id.id if rec.type == 'out' else rec.cash_id.default_account_id.id,
                'journal_id': rec.cash_id.id,
                'date': rec.date,
                'debit': total if rec.type == 'in_invoice' else 0,
                'credit': total if rec.type == 'out_invoice' else 0,
                # 'direct_expense_id': rec.sub_code,
#                 'partner_id': line.partner_id.id,
                'exclude_from_invoice_tab': True,
                'analytic_account_id': line.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                'amount_currency': total_currency,
                'currency_id': rec.currency_id.id if rec.currency_id.id != self.company_id.currency_id.id else False
            }
            lines.append((0, 0, othr_val))
            vals = {
                'name': rec.ref,
                'ref': rec.name or '',
                'move_type': 'entry',
                'currency_id': rec.currency_id.id,
                'company_id': rec.company_id.id,
                'date': rec.date,
                'journal_id': rec.cash_id.id,
                'narration': rec.description,
                'line_ids': lines
            }
            invoice = self.env['account.move'].sudo().create(vals).with_user(self.env.uid)
            invoice.message_post_with_view('mail.message_origin_link',
                                           values={'self': invoice, 'origin': rec},
                                           subtype_id=self.env.ref('mail.mt_note').id)

            return invoice

    @api.model_create_multi
    def re_confirm_move_values(self, move):
        if move:
            move.line_ids.unlink()
            for rec in self:
                lines = [(5, 0, 0)]
                total = 0
                for line in rec.line_ids:
                    taxes = line.tax_id.with_context(round=True).compute_all(
                        line.amount, rec.currency_id, 1,
                        False)
                    total += line.amount
                    line_vals = {
                        'move_id': move.id,
                        'name': line.description,
                        'account_id': line.account_id.id,
                        'journal_id': rec.cash_id.id,
                        'date': rec.date,
                        'partner_id': line.partner_id.id,
                        'debit': line.amount if rec.type == 'out_invoice' else 0,
                        'credit': line.amount if rec.type == 'in_invoice' else 0,
                        'exclude_from_invoice_tab': True,
                        'analytic_account_id': line.analytic_account_id.id,
                        'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                        'tax_ids': [(6, 0, line.tax_id.ids)]
                    }
                    lines.append((0, 0, line_vals))
                    for tax in taxes['taxes']:
                        if tax['tax_repartition_line_id']:
                            rep_ln = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
                            base_amount = self.env['account.move']._get_base_amount_to_display(tax['base'], rep_ln)
                        else:
                            base_amount = None
                        amount = tax['amount']

                        total += amount
                        move_line_tax_values = {
                            'move_id': move.id,
                            'name': tax['name'],
                            'quantity': 1,
                            'debit': amount if amount > 0 else 0,
                            'credit': -amount if amount < 0 else 0,
                            'account_id': tax['account_id'],
                            'tax_repartition_line_id': tax['tax_repartition_line_id'],
                            'tag_ids': tax['tag_ids'],
                            'tax_base_amount': base_amount,
#                             'partner_id': line.partner_id.id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                        }
                        lines.append((0, 0, move_line_tax_values))
                othr_val = {
                    'move_id': move.id,
                    'name': rec.ref,
                    'account_id': rec.cash_id.default_account_id.id if rec.type == 'out' else rec.cash_id.default_account_id.id,
                    'journal_id': rec.cash_id.id,
                    'date': rec.date,
#                     'partner_id': line.partner_id.id,
                    'debit': total if rec.type == 'in_invoice' else 0,
                    'credit': total if rec.type == 'out_invoice' else 0,
                    'exclude_from_invoice_tab': True
                }
                lines.append((0, 0, othr_val))
                vals = {
                    'ref': rec.name or '',
                    'move_type': 'entry',
                    'currency_id': rec.currency_id.id,
                    'company_id': rec.company_id.id,
                    'date': rec.date,
                    'journal_id': rec.cash_id.id,
                    'narration': rec.description,
                    'line_ids': lines
                }
                invoice = move.sudo().write(vals)
                return invoice

    def action_confirm(self):
        for rec in self:
            if len(rec.line_ids) > 0:
                if not self.posted_before:
                    res = self._prepare_move_values()
                    self.write({'move_id': res.id, 'state': 'approve', 'posted_before': True})
                    res.write({'document_id': rec.id})
                else:
                    res = self.re_confirm_move_values(move=rec.move_id)
                    self.write({'move_id': rec.move_id, 'state': 'approve'})
            else:
                raise ValidationError(_('You must add at least one line'))

    def action_post(self):
        for rec in self:
            move = self.env['account.move'].search([('id', '=', rec.move_id.id)])
            move.post()
            rec.write({'move_id': rec.move_id.id, 'state': 'posted'})

    def action_cancel(self):
        for rec in self:
            move = self.env['account.move'].search([('id', '=', rec.move_id.id)])
            if move:
                move.button_cancel()
            rec.write({'state': 'cancel'})

    def action_set_draft(self):
        for rec in self:
            move = self.env['account.move'].search([('id', '=', rec.move_id.id)])
            if move:
                move.button_draft()
            rec.write({'state': 'draft'})

    def print_check_out(self):
        partner = self.description
        lines = []
        if self.line_ids:
            for line in self.line_ids:
                val = {
                    'amount_taxed': line.amount_taxed,
                    'description': line.description,
                    'analytic_account_id': line.analytic_account_id.name,
                    'account_id': line.account_id.name
                }
                lines.append(val)
                if line.partner_id:
                    partner = line.partner_id.name
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'name': self.name,
                'partner_id': partner,
                'payment_date': self.date,
                'amount': self.amount_total,
                'communication': self.description,
                'amount_text': self.amount_text,
                'ref': self.ref,
                'lines': lines
            },
        }
        return self.env.ref('cash_management.check_out').report_action(self, data=data)

    def print_check_in(self):
        partner = self.description
        lines = []
        if self.line_ids:
            for line in self.line_ids:
                val = {
                    'amount_taxed': line.amount_taxed,
                    'description': line.description,
                    'analytic_account_id': line.account_id.code,
                    'account_id': line.account_id.name
                }
                lines.append(val)
                if line.partner_id:
                    partner = line.partner_id.name
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'name': self.name,
                'partner_id': partner,
                'payment_date': self.date,
                'amount': self.amount_total,
                'communication': self.description,
                'amount_text': self.amount_text,
                'ref': self.ref,
                'lines': lines,
                'income_type': self.income_type,
                'income_serial': self.income_serial,
                'income_department': self.income_department
            },
        }
        return self.env.ref('cash_management.check_in').report_action(self, data=data)


class CustomCashLine(models.Model):
    _name = 'direct.expense.lines'

    name = fields.Char()
    direct_expense_id = fields.Many2one("direct.expense")
    account_id = fields.Many2one("account.account", required=True,
                                 domain="[('user_type_id.name', '!=', 'Bank and Cash')]")
    analytic_account_id = fields.Many2one("account.analytic.account")
    description = fields.Char()
    partner_id = fields.Many2one("res.partner")
    tax_id = fields.Many2many(comodel_name='account.tax', string='Taxes', context={'active_test': False})
    amount = fields.Float(required=True)
    amount_taxed = fields.Float(required=True)
    amount_currency = fields.Monetary(string='Amount in Currency', store=True, copy=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    @api.onchange('tax_id', 'amount', 'partner_id')
    def onchange_method(self):
        for line in self:
            taxes = line.tax_id.with_context(round=True).compute_all(
                line.amount, line.direct_expense_id.currency_id, 1, False)
            total = 0
            taxes_val = 0

            for tax in taxes['taxes']:
                taxes_val += tax['amount']

            total += line.amount + taxes_val
            line.amount_taxed = total
