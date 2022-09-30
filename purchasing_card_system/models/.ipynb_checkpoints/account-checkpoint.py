from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'account.payment'
    installment_id = fields.Many2one('card.purchase.installment')
class ProductTemplate(models.Model):
    _inherit = 'account.move'
    card_purchase_invoice_id = fields.Many2one('card.purchase')
    card_purchase_bill_id = fields.Many2one('card.purchase')
