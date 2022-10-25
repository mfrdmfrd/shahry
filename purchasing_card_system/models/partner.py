from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'res.partner'
    interest_account_id = fields.Many2one('account.account',domain = [('internal_type','=','receivable')])
    admin_account_id = fields.Many2one('account.account',domain = [('internal_type','=','receivable')])
    penalty_account_id = fields.Many2one('account.account',domain = [('internal_type','=','receivable')])

    is_tax_registeerd = fields.Boolean()
    is_pre_payment = fields.Boolean()    
    commission_type = fields.Selection([('days','Days'),('months','Months')],default = 'days')    
    commission_period = fields.Integer()    
    bank_name = fields.Char()    
    account_name = fields.Char() 
    branch_name = fields.Char()     
    account_number = fields.Char()     
    swift = fields.Char()     
    iban = fields.Char()     
    tax_registertion = fields.Char()     