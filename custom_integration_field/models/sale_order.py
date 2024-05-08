from odoo import models, fields, _, api

class CustomSOField(models.Model):
    _inherit = 'sale.order'

    vit_trxid = fields.Char(string="Transaction ID")
    is_invoiced = fields.Boolean(string="Invoiced", default=False)

    def action_confirm(self):
        # Panggil metode induk
        result = super(CustomSOField, self).action_confirm()

        # Set nilai vit_trxid pada stock.picking yang sesuai
        for picking in self.picking_ids:
            picking.write({'vit_trxid': self.vit_trxid})

        return result