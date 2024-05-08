import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
import time

class ValidateDeliveryOrder(models.Model):
    _inherit = 'stock.picking'

    def validate_delivery_orders(self):
        delivery_orders_to_validate = self.env['stock.picking'].search([('state', 'in', ('assigned', 'confirmed')), ('picking_type_id.name', '=', 'Delivery Orders')], limit=200)

        for delivery_order in delivery_orders_to_validate:
            for move_line in delivery_order.move_ids_without_package:
                move_line.quantity = move_line.product_uom_qty
            try:
                delivery_order.button_validate()

                print(f"Delivery Order {delivery_order.name} validated successfully.")

                # Pass the delivery_order as an argument to update_vit_trxid_in_done_picking
                self.update_vit_trxid_in_done_picking(delivery_order)

            except UserError as e:
                print(f"Error while validating Delivery Order {delivery_order.name}: {e}")

    def update_vit_trxid_in_done_picking(self, delivery_order):
        # Use the passed delivery_order as needed
        if delivery_order.sale_id and delivery_order.sale_id.vit_trxid:
            delivery_order.write({'vit_is_integrated': True})
