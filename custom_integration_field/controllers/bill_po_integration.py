from odoo import models, api

class PoToBills(models.Model):
    _inherit = 'purchase.order'

    def create_bills_from_po(self):
        # Maksimal jumlah pesanan per batch
        batch_size = 200

        to_invoice_orders = self.env['purchase.order'].search([
            ('invoice_status', '=', 'to invoice'),
        ])

        # Bagi `to_invoice_orders` menjadi batch
        for index in range(0, len(to_invoice_orders), batch_size):
            batch_orders = to_invoice_orders[index:index+batch_size]
            self.process_batch(batch_orders)

    def process_batch(self, orders):
        for order in orders:
            order.action_create_invoice()
            # order.action_post()
