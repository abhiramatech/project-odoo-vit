from odoo import models, fields, api

class SOToInvoice(models.Model):
    _inherit = 'sale.order'

    def buat_invoice(self):
        to_invoice_orders = self.search([
            ('is_invoiced', '=', False),
            ('invoice_status', '=', 'to invoice'),
            ('order_line', '!=', False)
        ], limit=200)

        for order in to_invoice_orders:
            if not order.order_line:
                print(f"No products found to invoice for order {order.name}. Skipping...")
                continue

            wizard = self.env['sale.advance.payment.inv'].with_context(
                active_ids=order.ids,
                active_model='sale.order',
            ).create({})

            try:
                wizard.create_invoices()
            except ValueError as e:
                print(f"Error creating invoices for order {order.name}: {str(e)}")
                continue

            for invoice in order.invoice_ids:
                if isinstance(invoice, str):
                    print("Encountered a string. Skipping...")
                    continue

                if invoice.state == 'draft':
                    if not invoice.vit_credit:
                        invoice.action_post()
                        invoice.write({'vit_trxid': order.vit_trxid, 'invoice_date': order.date_order})
                        order.write({'is_invoiced': True})
                        print(f"Invoice {invoice.name} posted successfully.")
                    else:
                        print(f"Invoice {invoice.name} skipped due to vit_credit.")
                else:
                    print(f"Invoice {invoice.name} is not in 'draft' state")

        # Perform any other necessary steps after creating invoices
