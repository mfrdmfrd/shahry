from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'account.payment'
    installment_id = fields.Many2one('card.purchase.installment')
class ProductTemplate(models.Model):
    _inherit = 'account.move'
    card_purchase_invoice_id = fields.Many2one('card.purchase')
    card_purchase_bill_id = fields.Many2one('card.purchase')

    @api.onchange('card_purchase_invoice_id','card_purchase_bill_id','move_type')
    def _set_values(self):
        card_purchase_id = self.card_purchase_invoice_id or self.card_purchase_bill_id
        if not(card_purchase_id):
            return
        lines = []
        if self.move_type == 'out_invoice':
            self.partner_id = card_purchase_id.customer_id.id
            lines.append((0,0,{
                'product_id' : card_purchase_id.installment_product_id.id,
                'name' : card_purchase_id.installment_product_id.name,
                'quantity' : 1,
                'price_unit' : card_purchase_id.total_installments_amount
            }))
            lines.append((0,0,{
                'product_id' : card_purchase_id.intrest_product_id.id,
                'name' : card_purchase_id.intrest_product_id.name,
                'quantity' : 1,
                'price_unit' : card_purchase_id.benefit_rate_amount
            }))
        elif self.move_type == 'in_invoice':
            lines.append((0,0,{
                'product_id' : card_purchase_id.installment_product_id.id,
                'name' : card_purchase_id.installment_product_id.name,
                'quantity' : 1,
                'price_unit' : card_purchase_id.total_installments_amount
            }))
        self.invoice_line_ids = lines

