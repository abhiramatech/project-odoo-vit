from odoo import models, fields, _

class CustomAccountPaymentField(models.Model):
    _inherit = 'account.payment'

    vit_trxid = fields.Char(string='Transaction  ID')
    vit_docnum = fields.Char(string='Invoice ID')
