from odoo import fields, models, _, api

class InheritRegisterPayment(models.TransientModel):
    _inherit = 'account.payment.register'

    vit_trxid = fields.Char(string='Transaction ID')
    vit_docnum = fields.Char(string='Invoice ID')

    def _create_payment_vals_from_wizard(self, invoice):
        payment_vals = super(InheritRegisterPayment, self)._create_payment_vals_from_wizard(invoice)
        payment_vals.update({
            'vit_trxid': self.vit_trxid,
            'vit_docnum': self.vit_docnum,
        })
        return payment_vals

    @api.model
    def default_get(self, fields):
        res = super(InheritRegisterPayment, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')

        if active_model == 'account.move' and 'invoice_ids' in fields:
            invoice = self.env[active_model].browse(active_ids[0])
            res.update({
                'vit_trxid': invoice.vit_trxid,
                'vit_docnum': invoice.vit_docnum,
            })
        return res