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


class AccountMove(models.Model):
    _inherit = 'account.move'

    direct_expense_id = fields.Char()
    document_seq = fields.Char()
    document_id = fields.Many2one('direct.expense')
    total_discount = fields.Float(digits='Product Price', compute='_compute_total_discount')
    total_before_discount = fields.Float(digits='Product Price', compute='_compute_total_discount')

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_unit',
                 'invoice_line_ids.discount', 'amount_total_signed')
    def _compute_total_discount(self):
        for rec in self:
            total_discount = 0
            for line in rec.invoice_line_ids:
                total_discount += (line.quantity * line.price_unit) * (line.discount/100)
            rec.total_discount = total_discount
            rec.total_before_discount = total_discount + rec.amount_total_signed

    def button_draft(self):
        super(AccountMove, self).button_draft()
        if self.document_id:
            doc = self.document_id
            doc.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self).create(vals_list)
        for move in moves:
            document = ''
            if move.journal_id.sub_type:
                for line in move.line_ids:
                    if line.account_id == move.journal_id.default_account_id or line.account_id == move.journal_id.default_account_id:
                        if line.balance > 0:
                            document = self.env['ir.sequence'].next_by_code(move.journal_id.sub_seq_in.code)
                        elif line.balance < 0:
                            document = self.env['ir.sequence'].next_by_code(move.journal_id.sub_seq_out.code)
            move.update({'document_seq': document})
        return moves


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    direct_expense_id = fields.Char()
    document_seq = fields.Char()

