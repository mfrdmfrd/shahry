from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _name = 'card.purchase'
    name = fields.Char()
    state = fields.Selection(selection = [('draft','Draft'),('running','Running'),('closed','Closed')],default = 'draft')
    customer_id = fields.Many2one('res.partner',required = True)
    vendor_id = fields.Many2one('res.partner',required = True)
    vendor_branch = fields.Char()
    installment_type = fields.Selection([('monthly','Monthly'),('quarterly','Quarterly'),('semi ','semi annually'),('annually','annually')],default = 'monthly',required = True)
    contract_id = fields.Many2one('card.contract',domain = "[('customer_id','=',customer_id),('state','=','confirmed')]",required = True)
    start_date = fields.Date(required = True)
    end_date = fields.Date(readonly = True)
    buying_date = fields.Date()
    installment_product_id = fields.Many2one('product.product',required = True)
    intrest_product_id = fields.Many2one('product.product',required = True)
    penalty_product_id = fields.Many2one('product.product',required = True)

    number_of_installments = fields.Integer(required = True)
    total_installments_amount = fields.Float()
    down_payment = fields.Float()
    actual_purchase_amount = fields.Float(compute = '_set_actual_purchase_amount')

    @api.depends('down_payment','total_installments_amount')
    def _set_actual_purchase_amount(self):
        for rec in self:
            rec.actual_purchase_amount = rec.down_payment + rec.total_installments_amount
    commission_rate = fields.Float(required = True)
    benefit_rate = fields.Float(required = True)
    benefit_rate_amount = fields.Float(compute = '_set_benefit_rate_amount')
    @api.model
    def create(self,vals):
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('card.purchase', sequence_date=None) or 'New'
        return res 
    @api.depends('benefit_rate','total_installments_amount')
    def _set_benefit_rate_amount(self):
        for rec in self:
            rec.benefit_rate_amount = 0
            rec.benefit_rate_amount = rec.total_installments_amount * rec.benefit_rate
    installment_amount = fields.Float(compute = '_set_installment_amount')
    @api.depends('number_of_installments','total_installments_amount')
    def _set_installment_amount(self):
        for rec in self:
            rec.installment_amount = rec.total_installments_amount / rec.number_of_installments if rec.number_of_installments else 0
    penalty_amount = fields.Float()
    installment_ids = fields.One2many('card.purchase.installment','purchase_id')
    item_ids = fields.One2many('card.purchase.item','purchase_id')
    amount_due = fields.Float(compute = '_set_amount_due')
    applied_penalty_amount = fields.Float(compute = '_set_penalty',store = True)
    discount_rate = fields.Float()
    amount_due_after_discount = fields.Float(compute = '_set_amount_due_after_discount')
    invoice_created = fields.Boolean(copy = False)
    admin_fees_invoice_created = fields.Boolean(copy = False)
    journal_id = fields.Many2one('account.journal',required = True)
    def apply_discount(self):
        benifet_rate_diffrence = 0
        for line in self.installment_ids:
            if line.payment_status != 'paid':
                benifet_rate_diffrence += line.benefit_rate_amount *  self.discount_rate
                line.discount = self.discount_rate
        vals = {
            'move_type' : 'entry',
            'ref' : f'{self.name} - discount entry',
            'card_purchase_inverse_id' : self.id,
            'line_ids' : [
                self.get_journal_line(account_id = self.customer_id.interest_account_id,partner = self.customer_id,credit = benifet_rate_diffrence),
                self.get_journal_line(account_id = self.intrest_product_id.property_account_income_id,partner = self.customer_id,debit = benifet_rate_diffrence),
            ]
        }
        self.is_discount_created = True
        m = self.env['account.move'].create(vals)
        m.action_post()
        return self.show_account_move(ids = self.inverse_entries_ids.ids)
    @api.depends('discount_rate','amount_due')
    def _set_amount_due_after_discount(self):
        for rec in self:
            rec.amount_due_after_discount = rec.amount_due * (1 - rec.discount_rate)
    @api.depends('installment_ids')
    def _set_amount_due(self):
        for rec in self:
            rec.amount_due = sum([l.due_amount for l in rec.installment_ids])
    @api.depends('installment_ids')
    def _set_penalty(self):
        for rec in self:
            rec.applied_penalty_amount = sum([l.actual_penalty_amount for l in rec.installment_ids])
    def running(self):
        self.contract_id._set_actual_credit_limit()
        if self.contract_id.actual_credit_limit < self.total_installments_amount:
            raise ValidationError('This Purchase Amount is more than the contract credit limit')
        number_of_months_map = {
            'monthly' : 1,
            'quarterly' : 3,
            'semi' : 6,
            'annually' : 12,
        }
        number_of_months = number_of_months_map[self.installment_type]
        current_date = self.start_date
        lines = []
        for _ in range(self.number_of_installments):
            self.end_date = current_date
            lines.append((0,0,self.prepare_line(current_date)))
            current_date += relativedelta(months=number_of_months)
        self.installment_ids = lines
        self.state = 'running'
    def prepare_line(self,date):
        amount = self.installment_amount
        benefit_rate_amount = self.benefit_rate * amount
        return {
            'due_date' : date,
            'amount' : amount,
            'benefit_rate_amount' : benefit_rate_amount,
        }
    invoice_ids = fields.One2many('account.move','card_purchase_invoice_id')
    bill_ids = fields.One2many('account.move','card_purchase_bill_id')
    inverse_entries_ids = fields.One2many('account.move','card_purchase_inverse_id')
    payment_entries_ids = fields.One2many('account.move','card_purchase_payment_id')
    is_discount_created = fields.Boolean(copy = False)
    count_bill = fields.Integer(compute = '_set_count')
    count_invoice = fields.Integer(compute = '_set_count')
    count_inverse = fields.Integer(compute = '_set_count')
    count_payment = fields.Integer(compute = '_set_count')
    @api.depends('invoice_ids','bill_ids')
    def _set_count(self):
        for rec in self:
            rec.count_bill = len(rec.bill_ids)
            rec.count_invoice = len(rec.invoice_ids)
            rec.count_inverse = len(rec.inverse_entries_ids)
            rec.count_payment = len(rec.payment_entries_ids)
    def show_account_move(self,context = {},ids = []):
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        context.update({'create': False, 'delete': False})
        action['context'] = context
        if len(ids) == 1:
            action['res_id'] = ids[0] 
        if len(ids) <= 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            action['views'] = form_view
        else:
            action['domain'] = [('id','in',ids)]
        return  action
    def show_invoice(self):
        return self.show_account_move(ids = self.invoice_ids.ids)
    def show_bill(self):
        return self.show_account_move(ids = self.bill_ids.ids)
    def show_inverse(self):
        return self.show_account_move(ids = self.inverse_entries_ids.ids)
    def show_payment(self):
        return self.show_account_move(ids = self.payment_entries_ids.ids)
    def create_bill(self):
        vals = {
            'partner_id' : self.vendor_id.id,
            'ref' : f'{self.name} - main bill',
            'card_purchase_bill_id' : self.id,
            'move_type' : 'in_invoice',
            'invoice_line_ids' : [(0,0,{
                'product_id' : self.installment_product_id.id,
                'name' : self.installment_product_id.name,
                'quantity' : 1,
                'price_unit' : self.total_installments_amount
            })
            ]
        }
        self.env['account.move'].create(vals)
        return self.show_account_move(ids = self.bill_ids.ids)
    def get_journal_line(self,account_id,partner = False,debit = 0,credit = 0):
        return (0,0,{
            'account_id' : account_id.id,
            'debit' : debit,
            'credit' : credit,
            'partner_id' : partner.id if partner else False
        })
    def create_invoice(self):
        vals = {
            'move_type' : 'entry',
            'ref' : f'{self.name} - main invoice',
            'card_purchase_invoice_id' : self.id,
            'line_ids' : [
                self.get_journal_line(account_id = self.customer_id.property_account_receivable_id,partner = self.customer_id,debit = self.total_installments_amount),
                self.get_journal_line(account_id = self.customer_id.interest_account_id,partner = self.customer_id,debit = self.benefit_rate_amount),
                self.get_journal_line(account_id = self.installment_product_id.property_account_income_id,partner = self.customer_id,credit = self.total_installments_amount),
                self.get_journal_line(account_id = self.intrest_product_id.property_account_income_id,partner = self.customer_id,credit = self.benefit_rate_amount),
            ]
        }
        m = self.env['account.move'].create(vals)
        m.action_post()
        self.invoice_created = True
        return self.show_account_move(ids = self.invoice_ids.ids)
    admin_fees_amount = fields.Float()
    admin_fees_product_id = fields.Many2one('product.product',required = True)
    def create_admin_fees_invoice(self):
        vals = {
            'move_type' : 'out_invoice',
            'ref' : f'{self.name} - admin fees invoice',
            'card_purchase_invoice_id' : self.id,
            'partner_id' : self.customer_id.id,
            'partner_account_id' : self.customer_id.admin_account_id.id,
            'invoice_line_ids' : [
                (0,0,{
                    'product_id' : self.admin_fees_product_id.id,
                    'quantity' : 1,
                    'price_unit' : self.admin_fees_amount
                })
            ]
        }
        m = self.env['account.move'].create(vals)
        m.action_post()
        self.admin_fees_invoice_created = True
        return self.show_account_move(ids = self.invoice_ids.ids)
    


class ProductTemplate(models.Model):
    _name = 'card.purchase.installment'
    purchase_id = fields.Many2one('card.purchase')
    due_date = fields.Date()
    amount = fields.Float()
    benefit_rate_amount = fields.Float()
    actual_benefit_rate_amount = fields.Float(compute = '_apply_discount',store = True)
    discount = fields.Float(default = 0)
    @api.depends('amount','benefit_rate_amount','discount')
    def _apply_discount(self):
        for rec in self:
            rec.actual_benefit_rate_amount = rec.benefit_rate_amount * (1 - rec.discount)
    actual_fees = fields.Float(compute = '_set_actual_fees',store = True)
    @api.depends('amount','actual_benefit_rate_amount')
    def _set_actual_fees(self):
        for rec in self:
            rec.actual_fees = rec.amount + rec.actual_benefit_rate_amount
    actual_amount = fields.Float(compute = '_set_actual_amount')
    last_penalty_applied_date = fields.Date()
    penalty_applied_ids = fields.One2many('card.purchase.penalty','line_id')
    def show_penalty(self):
        action = self.env.ref('purchasing_card_system.show_penalty_action').read()[0]
        action['res_id'] = self.id
        return action
    def apply_penalty(self):
        today = fields.Date().today()
        apply_before = fields.Date().today() - timedelta(days=3)
        recs = self.env['card.purchase.installment'].search([('due_date','<=',apply_before)])
        for rec in recs:
            if rec.payment_status != 'paid':
                penalty_vals = {
                    'line_id' : rec.id,
                    'date' : today,
                    'amount' : rec.purchase_id.penalty_amount
                }
                apply = False
                if not(rec.last_penalty_applied_date):
                    apply = True                    
                else:
                    after_week = rec.last_penalty_applied_date + timedelta(days=7)
                    if today >= after_week:
                        apply = True
                if apply:
                    self.env['card.purchase.penalty'].create(penalty_vals)
                    rec.last_penalty_applied_date = today
    penalty_amount = fields.Float(compute = '_set_penalty_amount',store = True)
    actual_penalty_amount = fields.Float(compute = '_set_penalty_amount',store = True)

    @api.depends('penalty_applied_ids.amount','penalty_applied_ids.actual_amount','penalty_applied_ids.is_waved')
    def _set_penalty_amount(self):
        for rec in self:
            rec.penalty_amount = sum([p.amount for p in rec.penalty_applied_ids])
            rec.actual_penalty_amount = sum([p.actual_amount for p in rec.penalty_applied_ids])
    @api.depends('actual_fees','due_date','actual_penalty_amount')
    def _set_actual_amount(self):
        for rec in self:
            today = fields.Date().today()
            rec.actual_amount = rec.actual_fees + rec.actual_penalty_amount
    payment_ids = fields.One2many('account.payment','installment_id')
    payment_reference = fields.Char()
    paid_amount = fields.Float()
    due_amount = fields.Float()
    payment_status = fields.Selection(selection = [('not_paid','Not Paid'),('partial','partially paid'),('paid','Paid')])
    def create_benifet_invoice(self):
        vals = {
            'move_type' : 'out_invoice',
            'ref' : f'{self.purchase_id.name} {self.due_date} installment - benifete  invoice',
            'card_purchase_invoice_id' : self.purchase_id.id,
            'partner_id' : self.purchase_id.customer_id.id,
            'partner_account_id' : self.purchase_id.customer_id.interest_account_id.id,
            'invoice_line_ids' : [
                (0,0,{
                    'product_id' : self.purchase_id.intrest_product_id.id,
                    'quantity' : 1,
                    'price_unit' : self.actual_benefit_rate_amount
                })
            ]
        }
        m = self.env['account.move'].create(vals)
        m.action_post()
    def create_benifet_inverse_entry(self):
        vals = {
            'move_type' : 'entry',
            'ref' : f'{self.purchase_id.name} {self.due_date} installment  - benifete inverse entry',
            'card_purchase_inverse_id' : self.purchase_id.id,
            'line_ids' : [
                self.purchase_id.get_journal_line(account_id = self.purchase_id.customer_id.interest_account_id,partner = self.purchase_id.customer_id,credit = self.actual_benefit_rate_amount),
                self.purchase_id.get_journal_line(account_id = self.purchase_id.intrest_product_id.property_account_income_id,partner = self.purchase_id.customer_id,debit = self.actual_benefit_rate_amount),
            ]
        }
        m = self.env['account.move'].create(vals)
        m.action_post()
    def create_penalty_invoice(self):
        vals = {
            'move_type' : 'out_invoice',
            'ref' : f'{self.purchase_id.name} {self.due_date} installment - penalty  invoice',
            'card_purchase_invoice_id' : self.purchase_id.id,
            'partner_id' : self.purchase_id.customer_id.id,
            'partner_account_id' : self.purchase_id.customer_id.penalty_account_id.id,
            'invoice_line_ids' : [
                (0,0,{
                    'product_id' : self.purchase_id.penalty_product_id.id,
                    'quantity' : 1,
                    'price_unit' : self.actual_penalty_amount
                })
            ]
        }
        m = self.env['account.move'].create(vals)
        m.action_post()
    def create_payment_entry(self):
        vals = {
            'move_type' : 'entry',
            'ref' : f'{self.purchase_id.name} {self.due_date} installment  - payment entry',
            'card_purchase_payment_id' : self.purchase_id.id,
        }
        interest = self.actual_benefit_rate_amount
        principle = self.amount
        penalty = self.actual_penalty_amount
        lines = [
            self.purchase_id.get_journal_line(account_id = self.purchase_id.journal_id.default_account_id,partner = False,debit = interest + penalty),
            self.purchase_id.get_journal_line(account_id = self.purchase_id.vendor_id.property_account_payable_id,partner = self.purchase_id.vendor_id,debit = principle),
            self.purchase_id.get_journal_line(account_id = self.purchase_id.customer_id.property_account_receivable_id,partner = self.purchase_id.customer_id,credit = principle),
            self.purchase_id.get_journal_line(account_id = self.purchase_id.customer_id.interest_account_id,partner = self.purchase_id.customer_id,credit = interest),
        ]
        if penalty:
            lines.append(self.purchase_id.get_journal_line(account_id = self.purchase_id.customer_id.penalty_account_id,partner = self.purchase_id.customer_id,credit = penalty))
        vals['line_ids'] = lines
        move = self.env['account.move'].create(vals)
        self.payment_reference = move.name 
        move.action_post()

    def pay(self):
        rec = self
        self.create_benifet_invoice()
        self.create_benifet_inverse_entry()
        if self.actual_penalty_amount:
            self.create_penalty_invoice()
        self.create_payment_entry()
        rec.paid_amount = rec.actual_amount
        rec.due_amount = 0 
        rec.payment_status = 'paid'
class ProductTemplate(models.Model):
    _name = 'card.purchase.penalty'
    date = fields.Date()
    amount = fields.Float()
    actual_amount = fields.Float(compute = '_set_actual_amount',store = True)
    line_id = fields.Many2one('card.purchase.installment')
    is_waved = fields.Boolean()
    @api.depends('is_waved','actual_amount')
    def _set_actual_amount(self):
        for rec in self:
            rec.actual_amount = rec.amount if not(rec.is_waved) else 0
    def wave_penalty(self):
        self.is_waved = True
class ProductTemplate(models.Model):
    _name = 'card.purchase.item'
    product_id = fields.Many2one('product.product',required = True)
    category_id = fields.Many2one('product.category',required = True)
    internal_category_id = fields.Many2one('product.category',required = True)
    price = fields.Float(required = True)
    purchase_id = fields.Many2one('card.purchase')

    

    

