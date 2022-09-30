from odoo import models, fields, api

class ProductTemplate(models.Model):
    _name = 'card.contract'
    name = fields.Char()
    customer_id = fields.Many2one('res.partner',required = True)
    state = fields.Selection(selection = [('draft','Draft'),('confirmed','Confirmed'),('cancelled','Cancelled')],default = 'draft',readonly = True)
    start_date = fields.Date(required = True)
    end_date = fields.Date(required = True)
    signing_date = fields.Date(required = True)
    benefit_rate = fields.Float()
    credit_limit = fields.Float()
    purchase_ids = fields.One2many('card.purchase','contract_id',readonly = True)
    actual_credit_limit = fields.Float(compute = '_set_actual_credit_limit',store = True)
    @api.depends('purchase_ids','credit_limit')
    def _set_actual_credit_limit(self):
        for rec in self:
            used_credit = sum([p.total_installments_amount for p in rec.purchase_ids if rec.state != 'draft'])
            rec.actual_credit_limit = rec.credit_limit - used_credit
    

    def confirm(self):
        self.state = 'confirmed'
    def cancel(self):
        self.state = 'cancelled'

    @api.model
    def create(self,vals):
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('card.contract', sequence_date=None) or 'New'
        return res
