from odoo import models, fields, _, api, exceptions

class CustomInvoiceField(models.Model):
    _inherit = 'account.move'

    vit_trxid = fields.Char(string="Transaction ID")
    vit_ref = fields.Char(string="Ref Number")
    vit_credit = fields.Boolean(string="Is Credit Note")
    vit_type = fields.Char(string="Transaction Type")
    vit_GR = fields.Boolean(string="Goods Receipt")
    vit_GI = fields.Boolean(string="Goods Issue")
