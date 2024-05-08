import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
from collections import defaultdict
import time
import pymssql

class IntegrationSalesOrder(models.Model):
    _inherit = 'sale.order'

    BATCH_SIZE = 100  

    def SalesOrder_Integration(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()
            log_error = self.env['log.note.error']

            update_date_sync_query = """
                UPDATE t_inv_h
                SET date_sync = GETDATE();

                UPDATE t_inv_d
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()

            query = """
                SELECT
                    h.doc_number,
                    h.customer_code,
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,  -- Format date to 'yyyy-mm-dd'
                    CONVERT(VARCHAR, h.date_sync, 23) as date_sync,
                    h.sync_flag,
                    h.sync_desc,
                    d.item_code,
                    d.item_name,
                    d.quantity,
                    d.price_unit,
                    CONVERT(VARCHAR, d.date_sync, 23) as date_sync_detail,
                    d.sync_flag,
                    d.sync_desc,
                    d.line_number,
                    d.doc_number,
                    CONVERT(VARCHAR, h.date_insert, 23) as date_inserts
                FROM
                    t_inv_h h
                INNER JOIN
                    t_inv_d d ON h.doc_number = d.doc_number
            """

            cursor.execute(query)
            sql_data = cursor.fetchall()

            grouped_data = defaultdict(list)
            for res in sql_data:
                doc_number = res[0]
                grouped_data[doc_number].append(res)

            # Initialize lists to store queries
            insert_log_queries = []
            update_sync_flag_queries = []
            insert_t_inv_h_log_queries = []
            insert_t_inv_d_log_queries = []
            create_sale_order = []
            delete_query_list = []

            for doc_number, data_list in grouped_data.items():
                customer_code = data_list[0][1]
                date_doc = data_list[0][2]
                date_insert = data_list[0][15]

                existing_receipt = self.env['sale.order'].search([('vit_trxid', '=', doc_number)])
                if existing_receipt:
                    continue

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[6])])]
                registered_products = [data for data in data_list if data[6] and self.env['product.product'].search([('default_code', '=', data[6])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[6] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"SO tidak bisa terbuat karena produk tidak terdaftar\n"
                        error_description += "\n".join([f"Item Code: {item_code}" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Sales Order',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })

                        insert_log_note_query = f"""
                            INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                            VALUES ('Sales Order', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', '{date_insert}', GETDATE());
                        """
                        update_sync_flag_query = f"""
                            UPDATE t_inv_h
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_inv_d
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';
                        """
                        # Accumulate queries in lists
                        insert_log_queries.append(insert_log_note_query)
                        update_sync_flag_queries.append(update_sync_flag_query)

                else:
                    # Calculate total amount from t_inv_d for the current doc_number
                    total_amount_t_inv_d = sum(float(data[8]) * float(data[9]) for data in registered_products)

                    # Fetch payment information from t_pay_inv for the current doc_number
                    payment_info_query = """
                        SELECT SUM(amount) FROM t_pay_inv WHERE ref_id = '{}'
                    """.format(doc_number)
                    cursor.execute(payment_info_query)
                    total_amount_t_pay_inv = cursor.fetchone()[0]

                    # Check if total amounts match
                    if abs(total_amount_t_inv_d  != total_amount_t_pay_inv):
                        error_description = f"Terjadi perbedaan total amount antara invoice dan payment {doc_number}"
                        existing_logs = log_error.search([('vit_jubelio_key', '=', doc_number)])
                        if not existing_logs:
                            log_error.create({
                                'vit_doc_type': 'Sales Order',
                                'vit_jubelio_key': doc_number,
                                'vit_sync_trx_date': date_doc,
                                'vit_sync_status': 'Failed',
                                'vit_sync_desc': error_description,
                            })

                            # Log the error and update sync_flag with error description
                            update_sync_flag_query = f"""
                                UPDATE t_inv_h
                                SET sync_flag = 0,
                                    sync_desc = '{error_description}'
                                WHERE doc_number = '{doc_number}';

                                UPDATE t_inv_d
                                SET sync_flag = 0,
                                    sync_desc = '{error_description}'
                                WHERE doc_number = '{doc_number}';
                            """
                            # Accumulate queries in lists
                            update_sync_flag_queries.append(update_sync_flag_query)
                    else:
                        # Proceed with creating the sales order
                        customers = self.env['res.partner'].search([('vit_customer_code', '=', customer_code)])
                        list_order_line = []
                        for data in registered_products:
                            line_number = data[13]
                            doc_number_detail = data[14]
                            item_code = data[6]
                            item_name = data[7]
                            qty = float(data[8])
                            price_unit = float(data[9])

                            # Add lines to the Goods Receipt
                            product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                            if product:
                                insert_t_inv_d_log_query = f"""
                                    INSERT INTO t_inv_d_log (doc_number, line_number, item_code, item_name, quantity, price_unit, date_sync, date_insert, sync_flag, sync_desc)
                                    VALUES ('{doc_number_detail}', '{line_number}', '{item_code}', '{item_name}', '{qty}', '{price_unit}', '{date_insert}', GETDATE(), 1, NULL);
                                """
                                insert_t_inv_d_log_queries.append(insert_t_inv_d_log_query)
                                sale_order_line = (0, 0, {
                                    'product_id': product.id,
                                    'product_template_id': product.id,
                                    'product_uom_qty': qty,
                                    'name': item_name,
                                    'price_unit': price_unit,
                                })
                                list_order_line.append(sale_order_line)

                        sales_order = self.env['sale.order'].create({
                            'partner_id': customers.id,
                            'validity_date': date_doc,
                            'date_order': date_doc,
                            'vit_trxid': doc_number,
                            'order_line': list_order_line,
                        })
                        sales_order.action_confirm()
                        sales_order.write({'date_order': date_doc})
    
                        # Accumulate queries in lists
                        update_sync_flag_registered_query = f"""
                            UPDATE t_inv_h
                            SET sync_flag = 1,
                                sync_desc = NULL
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_inv_d
                            SET sync_flag = 1,
                                sync_desc = NULL
                            WHERE doc_number = '{doc_number}';
                        """
                        insert_t_inv_h_log_query = f"""
                            INSERT INTO t_inv_h_log (doc_number, customer_code, date_doc, date_insert, date_sync, sync_flag, sync_desc)
                            VALUES ('{doc_number}', '{customer_code}', '{date_doc}', '{date_insert}', GETDATE(), 1, NULL);
                        """
                    
                        update_sync_flag_queries.append(update_sync_flag_registered_query)
                        insert_t_inv_h_log_queries.append(insert_t_inv_h_log_query)

            # Execute batch update queries
            self.execute_batch_queries(conn, cursor, insert_log_queries)
            self.execute_batch_queries(conn, cursor, update_sync_flag_queries)
            self.execute_batch_queries(conn, cursor, insert_t_inv_h_log_queries)
            self.execute_batch_queries(conn, cursor, insert_t_inv_d_log_queries)

            delete_query_value_null = f"""
                DELETE FROM t_inv_h
                WHERE sync_flag = 1;

                DELETE FROM t_inv_d
                WHERE sync_flag = 1;
            """
            delete_query_list.append(delete_query_value_null)
            self.execute_batch_queries(conn, cursor, delete_query_list)

        finally:
            conn.close()

    def execute_batch_queries(self, conn, cursor, queries):
        """Execute a batch of queries in a single database transaction."""
        try:
            for i in range(0, len(queries), self.BATCH_SIZE):
                batch = queries[i:i + self.BATCH_SIZE]
                for query in batch:
                    cursor.execute(query)
                conn.commit()
        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error executing batch queries: {error_message}")
        

    def Re_SYNC_SaleOrder(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()
            log_error = self.env['log.note.error']

            query = """
                SELECT
                    h.doc_number,
                    h.customer_code,
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,  -- Format date to 'yyyy-mm-dd'
                    CONVERT(VARCHAR, h.date_sync, 23) as date_sync,
                    h.sync_flag,
                    h.sync_desc,
                    d.item_code,
                    d.item_name,
                    d.quantity,
                    d.price_unit,
                    CONVERT(VARCHAR, d.date_sync, 23) as date_sync_detail,
                    d.sync_flag,
                    d.sync_desc,
                    d.line_number,
                    d.doc_number,
                    CONVERT(VARCHAR, h.date_insert, 23) as date_inserts
                FROM
                    t_inv_h_log h
                INNER JOIN
                    t_inv_d_log d ON h.doc_number = d.doc_number
            """

            cursor.execute(query)
            sql_data = cursor.fetchall()

            grouped_data = defaultdict(list)
            for res in sql_data:
                doc_number = res[0]
                grouped_data[doc_number].append(res)

            # Initialize lists to store queries
            insert_log_queries = []
            update_sync_flag_queries = []
            insert_t_inv_h_log_queries = []
            insert_t_inv_d_log_queries = []
            create_sale_order = []
            delete_query_list = []

            for doc_number, data_list in grouped_data.items():
                customer_code = data_list[0][1]
                date_doc = data_list[0][2]
                date_insert = data_list[0][15]

                existing_receipt = self.env['sale.order'].search([('vit_trxid', '=', doc_number)])
                if existing_receipt:
                    continue

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[6])])]
                registered_products = [data for data in data_list if data[6] and self.env['product.product'].search([('default_code', '=', data[6])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[6] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"SO tidak bisa terbuat karena produk tidak terdaftar\n"
                        error_description += "\n".join([f"Item Code: {item_code}" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Sales Order',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })
                else:
                    # Proceed with creating the sales order
                    customers = self.env['res.partner'].search([('vit_customer_code', '=', customer_code)])
                    list_order_line = []
                    for data in registered_products:
                        line_number = data[13]
                        doc_number_detail = data[14]
                        item_code = data[6]
                        item_name = data[7]
                        qty = float(data[8])
                        price_unit = float(data[9])

                        # Add lines to the Goods Receipt
                        product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                        if product:
                            sale_order_line = (0, 0, {
                                'product_id': product.id,
                                'product_template_id': product.id,
                                'product_uom_qty': qty,
                                'name': item_name,
                                'price_unit': price_unit,
                            })
                            list_order_line.append(sale_order_line)

                    sales_order = self.env['sale.order'].create({
                        'partner_id': customers.id,
                        'validity_date': date_doc,
                        'date_order': date_doc,
                        'vit_trxid': doc_number,
                        'order_line': list_order_line,
                    })
                    sales_order.action_confirm()
                    sales_order.write({'date_order': date_doc})
        finally:
            conn.close()