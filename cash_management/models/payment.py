from decimal import Decimal

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, except_orm, ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    account_to = fields.Many2one("account.account", string="Account")

    @api.depends('invoice_line_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for payment in self:
            # if payment.line_ids:
            #     payment.destination_account_id = payment.line_ids.mapped(
            #         'line_ids.account_id').filtered(
            #         lambda account: account.user_type_id.type in ('receivable', 'payable'))[0]
            if payment.payment_type == 'transfer':
                if not payment.company_id.transfer_account_id.id:
                    raise UserError(
                        _('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
                payment.destination_account_id = payment.company_id.transfer_account_id.id
            elif payment.partner_id:
                partner = payment.partner_id.with_context(force_company=payment.company_id.id)
                if payment.partner_type == 'customer':
                    if payment.account_to:
                        payment.destination_account_id = payment.account_to.id
                    else:
                        payment.destination_account_id = partner.property_account_receivable_id.id
                else:
                    if payment.account_to:
                        payment.destination_account_id = payment.account_to.id
                    else:
                        payment.destination_account_id = partner.property_account_payable_id.id
            elif payment.partner_type == 'customer':
                if payment.account_to:
                    payment.destination_account_id = payment.account_to.id
                else:
                    default_account = self.env['ir.property'].with_context(force_company=payment.company_id.id).get(
                        'property_account_receivable_id', 'res.partner')
                    payment.destination_account_id = default_account.id
            elif payment.partner_type == 'supplier':
                if payment.account_to:
                    payment.destination_account_id = payment.account_to.id
                else:
                    default_account = self.env['ir.property'].with_context(force_company=payment.company_id.id).get(
                        'property_account_payable_id', 'res.partner')
                    payment.destination_account_id = default_account.id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.payment_type == 'inbound':
            self.account_to = self.partner_id.property_account_receivable_id.id
        elif self.payment_type == 'outbound':
            self.account_to = self.partner_id.property_account_payable_id.id

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type == 'inbound':
            self.account_to = self.partner_id.property_account_receivable_id.id
        elif self.payment_type == 'outbound':
            self.account_to = self.partner_id.property_account_payable_id.id

