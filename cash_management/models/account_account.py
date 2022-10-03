import json

from odoo import models, api, _, fields, tools
from odoo.exceptions import AccessError, except_orm, ValidationError, UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    dont_allow_deb = fields.Boolean("Don't Allow Debit Balance")
    dont_allow_crd = fields.Boolean("Don't Allow Credit Balance")
