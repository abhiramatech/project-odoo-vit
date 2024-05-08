import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
from collections import defaultdict
import time
import pymssql

class IntegrationPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def PurchaseOrder_Integration(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()
            log_error = self.env['log.note.error']

            update_date_sync_query = """
                UPDATE t_grpo_h
                SET date_sync = GETDATE();

                UPDATE t_grpo_d
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()

            query = """
                SELECT
                    h.doc_number,
                    h.vendor_code,
                    h.ref_id,
                    h.date_doc,
                    h.date_sync,
                    h.sync_flag,
                    h.sync_desc,
                    d.item_code,
                    d.qty,
                    d.price_unit,
                    d.date_sync,
                    d.sync_flag,
                    d.sync_desc,
                    d.doc_number,
                    d.line_number,
                    CONVERT(VARCHAR, h.date_insert, 23) as date_insert
                FROM
                    t_grpo_h h
                INNER JOIN
                    t_grpo_d d ON h.doc_number = d.doc_number;
            """

            cursor.execute(query)
            sql_data = cursor.fetchall()

            grouped_data = defaultdict(list)
            for res in sql_data:
                doc_number = res[0]
                grouped_data[doc_number].append(res)

            batch_size = 100
            order_count = 0
            batch = []

            for doc_number, data_list in grouped_data.items():
                vendor_code = data_list[0][1]
                ref_id = data_list[0][2]
                date_doc = data_list[0][3]
                date_insert = data_list[0][15]

                existing_receipt = self.env['purchase.order'].search([('vit_trxid', '=', doc_number)])
                if existing_receipt:
                    continue

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[7])])]
                registered_products = [data for data in data_list if data[7] and self.env['product.product'].search([('default_code', '=', data[7])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[7] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"PO tidak bisa terbuat karena produk\n"
                        error_description += "\n".join([f"-{item_code} tidak terdaftar" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Purchase Order',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })
                        update_sync_flag_query = f"""
                            UPDATE t_grpo_h
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_grpo_d
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';
                        """
                        cursor.execute(update_sync_flag_query)
                        conn.commit()

                        insert_log_note_query = f"""
                            INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                            VALUES ('Purchase Order', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', GETDATE(), GETDATE());
                        """
                        cursor.execute(insert_log_note_query)
                        conn.commit()
                else:
                    vendors = self.env['res.partner'].search([('vit_customer_code', '=', vendor_code)], limit=1)

                    purchase_order_line = []
                    for data in registered_products:
                        doc_num_detail = data[13]
                        line_number_detail = data[14]
                        item_code = data[7]
                        qty = float(data[8])
                        price_unit = float(data[9])

                        # Add lines to the Goods Receipt
                        product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                        if product:
                            insert_t_grpo_d_log_query = f"""
                                INSERT INTO t_grpo_d_log (doc_number, line_number, item_code, qty, price_unit, date_insert, date_sync, sync_flag, sync_desc)
                                VALUES ('{doc_num_detail}', '{line_number_detail}', '{item_code}', '{qty}', '{price_unit}', '{date_insert}', GETDATE(), 1, NULL);
                            """
                            cursor.execute(insert_t_grpo_d_log_query)
                            conn.commit()

                            order_line = (0, 0, {
                                'product_id': product.id,
                                'product_qty': qty,
                                'name': product.name,
                                'price_unit': price_unit,
                            })
                            purchase_order_line.append(order_line)

                    purchase_order = self.env['purchase.order'].create({
                        'partner_id': vendors.id,
                        'date_planned': date_doc,
                        'date_order': date_doc,
                        'vit_trxid': doc_number,
                        'vit_ref': ref_id,
                        'order_line': purchase_order_line,
                    })
                    update_sync_flag_registered_query = f"""
                        UPDATE t_grpo_h
                        SET sync_flag = 1,
                            sync_desc = NULL
                        WHERE doc_number = '{doc_number}';

                        UPDATE t_grpo_d
                        SET sync_flag = 1,
                            sync_desc = NULL
                        WHERE doc_number = '{doc_number}';
                    """
                    cursor.execute(update_sync_flag_registered_query)
                    conn.commit()

                    insert_t_grpo_h_log_query = f"""
                        INSERT INTO t_grpo_h_log (doc_number, vendor_code, ref_id, date_doc, date_insert, date_sync, sync_flag, sync_desc)
                        VALUES ('{doc_number}', '{vendor_code}', '{ref_id}', '{date_doc}', '{date_insert}', GETDATE(), 1, NULL);
                    """
                    cursor.execute(insert_t_grpo_h_log_query)
                    conn.commit()

                    batch.append(purchase_order)
                    order_count += 1

                    if order_count >= batch_size:
                        self.confirm_purchase_order_batch(batch, date_doc)
                        batch = []

            if batch:
                self.confirm_purchase_order_batch(batch, date_doc)

            delete_query_value_null = f"""
                DELETE FROM t_grpo_h
                WHERE sync_flag = 1;

                DELETE FROM t_grpo_d
                WHERE sync_flag = 1;
            """
            cursor.execute(delete_query_value_null)
            conn.commit()

            # Close the SQL Server connection
            conn.close()

        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error connecting to SQL Server: {error_message}")

    def confirm_purchase_order_batch(self, batch, date_doc):
        for order in batch:
            order.button_confirm()
            order.action_view_picking()

            # Update date_order field
            order.sudo().write({'date_order': date_doc})