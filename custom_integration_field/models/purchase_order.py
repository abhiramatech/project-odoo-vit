from odoo import models, fields, api

class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vit_trxid = fields.Char(string="Transaction ID")
    vit_ref = fields.Char(string="Reference ID")

    def button_confirm(self):
        # Panggil metode induk
        result = super(InheritPurchaseOrder, self).button_confirm()

        # Set nilai vit_trxid pada stock.picking yang sesuai
        for picking in self.picking_ids:
            picking.write({'vit_trxid': self.vit_trxid,
                           'vit_ref': self.vit_ref})
            picking.button_validate()

        return result
    
    def action_create_invoice(self):
        # Panggil metode induk
        result = super(InheritPurchaseOrder, self).action_create_invoice()

        # Ambil semua faktur yang telah dibuat untuk pesanan pembelian ini
        for invoice in self.invoice_ids:
            if invoice.move_type == 'in_invoice':
                invoice.write({'vit_trxid': self.vit_trxid, 'invoice_date': self.date_planned})
                invoice.action_post()

        return result
