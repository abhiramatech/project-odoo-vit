import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
from collections import defaultdict
import time
import pymssql

class ManualIntegrationReturnVendor(models.Model):
    _inherit = 'stock.picking'

    def confirm_rtv_batch(self, batch):
        for receipt in batch:
            receipt.action_confirm()
            receipt.button_validate()

    def Manual_Sync_ReturnVendor_Integration(self, date_from, date_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()
            log_error = self.env['log.note.error']

            update_date_sync_query = """
                UPDATE t_rtv_h
                SET date_sync = GETDATE();

                UPDATE t_rtv_d
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()

            query = """
                SELECT
                    h.doc_number,
                    h.vendor_code,
                    h.ref_id,
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,
                    d.doc_number,
                    d.line_number,
                    d.item_code,
                    d.qty,
                    d.doc_number,
                    d.line_number,
                    CONVERT(VARCHAR, h.date_insert, 23) as date_insert
                FROM
                    t_rtv_h h
                INNER JOIN
                    t_rtv_d d ON h.doc_number = d.doc_number
                WHERE 
                    h.date_doc BETWEEN %s AND %s
                    AND h.sync_flag = 0;
            """

            cursor.execute(query, (date_from, date_to))
            sql_data = cursor.fetchall()

            grouped_data = defaultdict(list)
            for res in sql_data:
                doc_number = res[0]
                grouped_data[doc_number].append(res)

            batch_size = 2000
            order_count = 0
            batch = []

            for doc_number, data_list in grouped_data.items():
                vendor_code = data_list[0][1]
                ref_id = data_list[0][2]
                date_doc = data_list[0][3]
                date_insert = data_list[0][10]

                existing_rtv = self.env['stock.picking'].search([('vit_trxid', '=', doc_number)])
                if existing_rtv:
                    continue

                operation_type_search = self.env['stock.picking.type'].search([('name', '=', 'Return to Vendor')])
                location_id = self.env['stock.location'].search([('complete_name', '=', "WH/Stock")], limit=1)

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[6])])]
                registered_products = [data for data in data_list if data[6] and self.env['product.product'].search([('default_code', '=', data[6])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[6] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"RTV tidak bisa terbuat karena produk tidak terdaftar\n"
                        error_description += "\n".join([f"Item Code: {item_code}" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Return To Vendor',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })
                        insert_log_note_query = f"""
                            INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                            VALUES ('Return To Vendor', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', GETDATE(), GETDATE());
                        """
                        cursor.execute(insert_log_note_query)
                        conn.commit()

                        update_sync_flag_query = f"""
                            UPDATE t_rtv_h
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_rtv_d
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';
                        """
                        cursor.execute(update_sync_flag_query)
                        conn.commit()
                else:
                    vendors = self.env['res.partner'].search([('vit_customer_code', '=', vendor_code), ('supplier_rank', '=', 1)], limit=1)
                    stock_move_doc = []
                    for data in registered_products:
                        item_code = data[6]
                        qty = float(data[7])
                        doc_num_detail = data[8]
                        line_number_detail = data[9]

                        source_loc = self.env['stock.location'].search([('complete_name', '=', "Partners/Vendors")], limit=1)

                        # Add lines to the Goods Receipt
                        product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                        if product:
                            insert_t_rtv_d_log_query = f"""
                                INSERT INTO t_rtv_d_log (doc_number, line_number, item_code, qty, date_insert, date_sync, sync_flag, sync_desc)
                                VALUES ('{doc_num_detail}', '{line_number_detail}', '{item_code}', '{qty}', '{date_insert}', GETDATE(), 1, NULL);
                            """
                            cursor.execute(insert_t_rtv_d_log_query)
                            conn.commit()

                            stock_move = (0, 0, {
                                'product_id': product.id,
                                'product_uom_qty': qty,
                                'quantity': qty,
                                'name': product.name,
                                'location_id': location_id.id,
                                'location_dest_id': source_loc.id.id,
                            })
                            stock_move_doc.append(stock_move)
                            
                    # Create Goods Receipt
                    rtv = self.env['stock.picking'].create({
                        'partner_id': vendors.id,  # Set the appropriate partner_id
                        'picking_type_id': operation_type_search.id,
                        'location_id': location_id.id,
                        'location_dest_id': source_loc.id,
                        'scheduled_date': date_doc,
                        'vit_trxid': doc_number,
                        'move_ids_without_package': stock_move_doc,
                    })
                    update_sync_flag_registered_query = f"""
                        UPDATE t_rtv_h
                        SET sync_flag = 1,
                            sync_desc = NULL
                        WHERE doc_number = '{doc_number}';

                        UPDATE t_rtv_d
                        SET sync_flag = 1,
                            sync_desc = NULL
                        WHERE doc_number = '{doc_number}';
                    """
                    cursor.execute(update_sync_flag_registered_query)
                    conn.commit()

                    insert_t_rtv_h_log_query = f"""
                        INSERT INTO t_rtv_h_log (doc_number, vendor_code, ref_id, date_doc, date_insert, date_sync, sync_flag, sync_desc)
                        VALUES ('{doc_number}', '{vendor_code}', '{ref_id}', '{date_doc}', '{date_insert}', GETDATE(), 1, NULL);
                    """
                    cursor.execute(insert_t_rtv_h_log_query)
                    conn.commit()

                    batch.append(rtv)
                    order_count += 1

                    if order_count >= batch_size:
                        self.confirm_rtv_batch(batch)
                        batch = []

            if batch:
                self.confirm_rtv_batch(batch)

            delete_query_value_null = f"""
                DELETE FROM t_rtv_h
                WHERE sync_flag = 1;

                DELETE FROM t_rtv_d
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

    @api.model
    def Searching_ReturnVendor(self, date_from, date_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                port=1433,
                                database='prado_odoo_prod', 
                                user='prdspradm', 
                                password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    h.doc_number,
                    h.vendor_code,
                    h.ref_id,
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,
                    h.sync_desc,
                    d.doc_number,
                    d.line_number,
                    d.item_code,
                    d.qty,
                    d.doc_number,
                    d.line_number
                FROM
                    t_rtv_h h
                INNER JOIN
                    t_rtv_d d ON h.doc_number = d.doc_number
                WHERE 
                    h.date_doc BETWEEN %s AND %s
                    AND (h.sync_flag = 0 OR h.sync_flag IS NULL);
            """
            cursor.execute(query, (date_from, date_to))
            sql_data = cursor.fetchall()

            return sql_data

        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error syncing data from SQL Server to Odoo: {error_message}")

        finally:
            # Close cursor and connection
            cursor.close()
            conn.close()