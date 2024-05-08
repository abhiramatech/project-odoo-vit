import pymssql
from odoo import models, fields, api, _

class Cancel_PO(models.Model):
    _inherit = 'account.move'

    @api.model
    def cancel_po(self):
        a = self.env['sale.order'].search([('state', '=', 'sale')], limit = 400)

        for x in a:
            so_cancel = self.env['sale.order.cancel'].with_context(
                active_model='sale.order', active_ids=x.ids
                ).create({'recipient_ids': False, 
                          'order_id': x.id,})

            so_cancel.action_cancel()

    @api.model
    def cancel_invoice(self):
        b = self.env['account.move'].search([('state', '=', 'posted'), ('move_type', '=', 'out_invoice')])

        for c in b:
            c.button_draft()

