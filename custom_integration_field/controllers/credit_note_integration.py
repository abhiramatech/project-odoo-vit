import pymssql
from odoo import models, fields, api, _
from collections import defaultdict

class IntegrationCreditNote(models.Model):
    _inherit = 'account.move'

    @api.model
    def CreditNote_Integration(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod',
                                   user='prdspradm',
                                   password='*112233*Sunter*')
            cursor = conn.cursor()

            update_date_sync_query = """
                UPDATE t_cn_h
                SET date_sync = GETDATE();

                UPDATE t_cn_d
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()
            
            log_error = self.env['log.note.error']

            query = """
                SELECT
                    h.doc_number,
                    h.customer_code,
                    h.ref_id,
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,
                    d.item_code,
                    d.item_name,
                    d.quantity,
                    d.price_unit,
                    d.doc_number,
                    d.line_number,
                    CONVERT(VARCHAR, h.date_insert, 23) as date_insert
                FROM
                    t_cn_h h
                INNER JOIN
                    t_cn_d d ON h.doc_number = d.doc_number
            """
            cursor.execute(query)
            sql_data = cursor.fetchall()

            grouped_data = defaultdict(list)
            for res in sql_data:
                doc_number = res[0]
                grouped_data[doc_number].append(res)

            batch_size = 2000
            order_count = 0
            batch = []

            for doc_number, data_list in grouped_data.items():
                customer_code = data_list[0][1]
                ref_id = data_list[0][2]
                date_doc = data_list[0][3]
                date_insert = data_list[0][10]

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[4])])]
                registered_products = [data for data in data_list if data[4] and self.env['product.product'].search([('default_code', '=', data[4])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[4] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"Credit Note tidak bisa terbuat karena produk tidak terdaftar\n"
                        error_description += "\n".join([f"Item Code: {item_code}" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Credit Note',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })
                        
                        update_sync_flag_registered_query = f"""
                            UPDATE t_cn_h
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_cn_d
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';
                        """
                        cursor.execute(update_sync_flag_registered_query)
                        conn.commit()

                        insert_log_note_query = f"""
                            INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                            VALUES ('Credit Note', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', GETDATE(), GETDATE());
                        """
                        cursor.execute(insert_log_note_query)
                        conn.commit()
                else:
                    existing_issue = self.env['account.move'].search([('vit_trxid', '=', doc_number), ('move_type', '=', 'out_refund')])
                    if not existing_issue:
                        partner_cn = self.env['res.partner'].search([('vit_customer_code', '=', customer_code)])
                        journal = self.env['account.journal'].search([('name', '=', 'Customer Invoices')])
                        credit_note_line = []
                        for data in registered_products:
                            item_code = data[4]
                            item_name = data[5]
                            qty = float(data[6])
                            price_unit = data[7]
                            doc_num_detail = data[8]
                            line_number_detail = data[9]

                            # Add lines to the Goods Issue
                            product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                            account_id = self.env['account.account'].search([('code', '=', "21130001")], limit=1).id
                            if product:
                                insert_t_cn_d_log_query = f"""
                                    INSERT INTO t_cn_d_log (doc_number, line_number, item_code, item_name, quantity, date_insert, date_sync, sync_flag, sync_desc)
                                    VALUES ('{doc_num_detail}', '{line_number_detail}', '{item_code}', '{item_name}','{qty}', '{date_insert}', GETDATE(), 1, NULL);
                                """
                                cursor.execute(insert_t_cn_d_log_query)
                                conn.commit()

                                details_gi = (0, 0, {
                                    'product_id': product.id,
                                    'quantity': qty,
                                    'price_unit': price_unit,
                                    'account_id': account_id,
                                })
                                credit_note_line.append(details_gi)

                        issue = self.env['account.move'].create({
                            'partner_id': partner_cn.id,
                            'journal_id': journal.id,
                            'date': date_doc,
                            'invoice_date': date_doc,
                            'vit_trxid': doc_number,
                            'vit_ref': ref_id,
                            'move_type': 'out_refund',
                            'invoice_line_ids': credit_note_line,
                        })
                        update_sync_flag_registered_query = f"""
                            UPDATE t_cn_h
                            SET sync_flag = 1,
                                sync_desc = NULL
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_cn_d
                            SET sync_flag = 1,
                                sync_desc = NULL
                            WHERE doc_number = '{doc_number}';
                        """
                        cursor.execute(update_sync_flag_registered_query)
                        conn.commit()

                        insert_t_cn_h_log_query = f"""
                            INSERT INTO t_cn_h_log (doc_number, customer_code, ref_id, date_doc, date_insert, date_sync, sync_flag, sync_desc)
                            VALUES ('{doc_number}', '{customer_code}', '{ref_id}', '{date_doc}', '{date_insert}', GETDATE(), 1, NULL);
                        """
                        cursor.execute(insert_t_cn_h_log_query)
                        conn.commit()
                        
                        batch.append(issue)
                        order_count += 1

                        if order_count >= batch_size:
                            self.confirm_credit_note_batch(batch)
                            batch = []
                    
            if batch:
                self.confirm_credit_note_batch(batch)

            # Close the SQL Server connection
            conn.close()

        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error connecting to SQL Server: {error_message}")
