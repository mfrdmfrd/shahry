from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _name = 'card.purchase'
    name = fields.Char()
    state = fields.Selection(selection = [('draft','Draft'),('running','Running'),('closed','Closed')],default = 'draft')
    customer_id = fields.Many2one('res.partner',required = True)
    installment_type = fields.Selection([('monthly','Monthly'),('quarterly','Quarterly'),('semi ','semi annually'),('annually','annually')],default = 'monthly',required = True)
    contract_id = fields.Many2one('card.contract',domain = "[('customer_id','=',customer_id),('state','=','confirmed')]",required = True)
    start_date = fields.Date(required = True)
    installment_product_id = fields.Many2one('product.product',required = True)
    intrest_product_id = fields.Many2one('product.product',required = True)
    number_of_installments = fields.Integer(required = True)
    total_installments_amount = fields.Float()
    benefit_rate = fields.Float(related = 'contract_id.benefit_rate')
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
            'actual_fees' : benefit_rate_amount + amount,
        }
    invoice_ids = fields.One2many('account.move','card_purchase_invoice_id')
    bill_ids = fields.One2many('account.move','card_purchase_bill_id')
    count_bill = fields.Integer(compute = '_set_count')
    count_invoice = fields.Integer(compute = '_set_count')
    @api.depends('invoice_ids','bill_ids')
    def _set_count(self):
        for rec in self:
            rec.count_bill = len(rec.bill_ids)
            rec.count_invoice = len(rec.invoice_ids)
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
    def create_bill(self):
        return self.show_account_move({'default_move_type': 'in_invoice','default_card_purchase_bill_id' : self.id})
    def create_invoice(self):
        return self.show_account_move({'default_move_type': 'out_invoice','default_card_purchase_invoice_id' : self.id})

class ProductTemplate(models.Model):
    _name = 'card.purchase.installment'
    purchase_id = fields.Many2one('card.purchase')
    due_date = fields.Date()
    amount = fields.Float()
    benefit_rate_amount = fields.Float()
    actual_fees = fields.Float()
    penalty_amount = fields.Float(compute = '_set_actual_amount')
    actual_amount = fields.Float(compute = '_set_actual_amount')
    @api.depends('actual_fees','due_date')
    def _set_actual_amount(self):
        for rec in self:
            today = fields.Date().today()
            penalty = rec.purchase_id.penalty_amount if today >= rec.due_date else 0
            rec.penalty_amount = penalty
            rec.actual_amount = rec.actual_fees + rec.penalty_amount
    payment_ids = fields.One2many('account.payment','installment_id')
    payment_reference = fields.Char(compute = 'payment_changes')
    paid_amount = fields.Float(compute = 'payment_changes')
    due_amount = fields.Float(compute = 'payment_changes')
    payment_status = fields.Selection(selection = [('not_paid','Not Paid'),('partial','partially paid'),('paid','Paid')],compute = 'payment_changes')
    @api.depends('payment_ids.state','payment_ids.amount','payment_ids.name','payment_ids.payment_type')
    def payment_changes(self):
        for rec in self:
            rec.payment_reference = ','.join([p.name for p in rec.payment_ids if p.state == 'posted' and p.payment_type == 'inbound'])
            sum_paid = sum([p.amount for p in rec.payment_ids if p.state == 'posted' and p.payment_type == 'inbound'])
            rec.paid_amount = sum_paid if sum_paid <= rec.actual_amount else rec.actual_amount
            rec.due_amount = rec.actual_amount - rec.paid_amount
            if rec.due_amount == 0:
                rec.payment_status = 'paid'
            elif rec.due_amount == rec.actual_amount:
                rec.payment_status = 'not_paid'
            else:
                rec.payment_status = 'partial'
    def pay(self):
        action = self.env.ref('account.action_account_payments').sudo().read()[0]
        action['context'] = {'default_payment_type': 'inbound','default_partner_type': 'customer','default_move_journal_types': ('bank', 'cash'),'default_partner_id' : self.purchase_id.customer_id.id,'default_amount' : self.due_amount,'default_installment_id' : self.id}
        form_view = [(self.env.ref('account.view_account_payment_form').id, 'form')]
        action['views'] = form_view 
        return action

    

    

