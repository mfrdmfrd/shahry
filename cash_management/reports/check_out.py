
from odoo import api, fields, models, _, tools


class CheckOutReport(models.AbstractModel):
    _name = 'report.cash_management.check_out_template'
    _description = "Check Out"

    def _get_report_values(self, docids, data=None):
        name = data['form']['name']
        partner_id = data['form']['partner_id']
        payment_date = data['form']['payment_date']
        amount = data['form']['amount']
        communication = data['form']['communication']
        amount_text = data['form']['amount_text']
        ref = data['form']['ref']
        lines = data['form']['lines']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'name': name,
                'partner_id': partner_id,
                'payment_date': payment_date,
                'amount': amount,
                'communication': communication,
                'amount_text': amount_text,
                'ref': ref,
                'lines': lines
        }


class CheckInReport(models.AbstractModel):
    _name = 'report.cash_management.check_in_template'
    _description = "Check In"

    def _get_report_values(self, docids, data=None):
        partner_id = data['form']['partner_id']
        payment_date = data['form']['payment_date']
        amount = data['form']['amount']
        communication = data['form']['communication']
        amount_text = data['form']['amount_text']
        lines = data['form']['lines']

        income_type = data['form']['income_type']
        income_serial = data['form']['income_serial']
        income_department = data['form']['income_department']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'partner_id': partner_id,
                'payment_date': payment_date,
                'amount': amount,
                'communication': communication,
                'amount_text': amount_text,
                'lines': lines,

                'income_type': income_type,
                'income_serial': income_serial,
                'income_department':income_department
        }


class CashOutReport(models.AbstractModel):
    _name = 'report.cash_management.cash_out_template'
    _description = "Cash Out"

    def _get_report_values(self, docids, data=None):
        partner_id = data['form']['partner_id']
        payment_date = data['form']['payment_date']
        amount = data['form']['amount']
        communication = data['form']['communication']
        amount_text = data['form']['amount_text']
        lines = data['form']['lines']
        total_debit = data['form']['total_debit']
        total_credit = data['form']['total_credit']
        check_number = data['form']['check_number']
        journal_name = data['form']['journal_name']
        name = data['form']['name']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'partner_id': partner_id,
                'payment_date': payment_date,
                'amount': amount,
                'communication': communication,
                'amount_text': amount_text,
                'lines': lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'check_number': check_number,
                'journal_name': journal_name,
                'name': name,
        }


class CashInReport(models.AbstractModel):
    _name = 'report.cash_management.cash_in_template'
    _description = "Cash In"

    def _get_report_values(self, docids, data=None):
        partner_id = data['form']['partner_id']
        payment_date = data['form']['payment_date']
        amount = data['form']['amount']
        communication = data['form']['communication']
        amount_text = data['form']['amount_text']
        lines = data['form']['lines']
        total_debit = data['form']['total_debit']
        total_credit = data['form']['total_credit']
        check_number = data['form']['check_number']
        journal_name = data['form']['journal_name']
        name = data['form']['name']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'partner_id': partner_id,
                'payment_date': payment_date,
                'amount': amount,
                'communication': communication,
                'amount_text': amount_text,
                'lines': lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'check_number': check_number,
                'journal_name': journal_name,
                'name': name,
        }


class CashRecOutReport(models.AbstractModel):
    _name = 'report.cash_management.cash_rec_out_template'
    _description = "Cash In"

    def _get_report_values(self, docids, data=None):
        partner_id = data['form']['partner_id']
        payment_date = data['form']['payment_date']
        amount = data['form']['amount']
        communication = data['form']['communication']
        amount_text = data['form']['amount_text']
        lines = data['form']['lines']
        total_debit = data['form']['total_debit']
        total_credit = data['form']['total_credit']
        check_number = data['form']['check_number']
        journal_name = data['form']['journal_name']
        name = data['form']['name']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'partner_id': partner_id,
                'payment_date': payment_date,
                'amount': amount,
                'communication': communication,
                'amount_text': amount_text,
                'lines': lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'check_number': check_number,
                'journal_name': journal_name,
                'name': name,
        }


class CashRecInReport(models.AbstractModel):
    _name = 'report.cash_management.cash_rec_in_template'
    _description = "Cash In"

    def _get_report_values(self, docids, data=None):
        partner_id = data['form']['partner_id']
        payment_date = data['form']['payment_date']
        amount = data['form']['amount']
        communication = data['form']['communication']
        amount_text = data['form']['amount_text']
        lines = data['form']['lines']
        total_debit = data['form']['total_debit']
        total_credit = data['form']['total_credit']
        check_number = data['form']['check_number']
        journal_name = data['form']['journal_name']
        name = data['form']['name']
        return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'partner_id': partner_id,
                'payment_date': payment_date,
                'amount': amount,
                'communication': communication,
                'amount_text': amount_text,
                'lines': lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'check_number': check_number,
                'journal_name': journal_name,
                'name': name,
        }
