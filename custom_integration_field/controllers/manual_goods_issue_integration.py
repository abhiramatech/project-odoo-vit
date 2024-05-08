import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
from collections import defaultdict
import time
import pymssql

class ManualIntegrationGoodsIssue(models.Model):
    _inherit = 'stock.picking'

    def confirm_issue_batch(self, batch, date_sync, move_type):
        for receipt in batch:
            receipt.action_confirm()
            receipt.button_validate()

            find_journal = self.env['account.move'].search([('ref', 'ilike', receipt.name)])
            if find_journal:
                for rec in find_journal:
                    rec.write({'vit_GI': True,
                               'vit_type': move_type,})

                # Create Journal Entries
                    journal_id = self.env['account.journal'].search([('name', '=', 'Inventory Valuation')], limit=1)
                    # Inisialisasi debit_account_id
                    debit_account_id = False

                    # Lakukan pencarian pertama berdasarkan move_type dan vit_move_type_1
                    search_domain_1 = [('vit_move_type_1', '=', move_type)]
                    debit_account_id = self.env['account.account'].search(search_domain_1, limit=1)

                    # Jika tidak ditemukan, lakukan pencarian kedua berdasarkan move_type dan vit_move_type_2
                    if not debit_account_id:
                        search_domain_2 = [('vit_move_type_2', '=', move_type)]
                        debit_account_id = self.env['account.account'].search(search_domain_2, limit=1)


                    interim_account = self.env['account.account'].search([('name', '=', 'Interim Stock')], limit=1)
                    move_lines = []

                    # Iterate through move lines associated with the move
                    for line in rec.line_ids:
                        # Create a credit line for the stock input account (assuming it's a simple setup)
                        if line.credit:
                            credit_line = (0, 0, {
                                'name': rec.ref,
                                'account_id': interim_account.id, 
                                'credit': line.credit,
                                'debit': 0.0,
                                'partner_id': rec.partner_id.id,
                            })
                            move_lines.append(credit_line)

                        # Create a debit line for the stock output account (assuming it's a simple setup)
                        elif line.debit:
                            debit_line = (0, 0, {
                                'name': rec.ref,
                                'account_id': debit_account_id.id,
                                'credit': 0.0,
                                'debit': line.debit,
                                'partner_id': rec.partner_id.id,
                            })
                            move_lines.append(debit_line)

                    # Create the Journal Entry
                    move = self.env['account.move'].create({
                        'journal_id': journal_id.id,
                        'date': rec.date,
                        'ref': f"Reconcile Of {rec.ref}",
                        'line_ids': move_lines,
                        'vit_GI': True,
                        'vit_type': move_type,
                    })

                    # Post the Journal Entry
                    move.action_post()

    def Manual_Sync_GoodsIssue_Integration(self, date_from, date_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()
            log_error = self.env['log.note.error']

            update_date_sync_query = """
                UPDATE t_gi_h
                SET date_sync = GETDATE();

                UPDATE t_gi_d
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()

            query = """
                SELECT
                    h.doc_number,
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,
                    h.move_type,
                    CONVERT(VARCHAR, h.date_sync, 23) as date_sync,
                    d.item_code,
                    d.qty,
                    h.sync_flag,
                    CONVERT(VARCHAR, d.date_sync, 23) as date_sync,
                    d.sync_flag,
                    h.sync_desc,
                    d.sync_desc,
                    d.doc_number,
                    d.line_number,
                    CONVERT(VARCHAR, h.date_insert, 23) as date_insert
                FROM
                    t_gi_h h
                INNER JOIN
                    t_gi_d d ON h.doc_number = d.doc_number
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
                date_doc = data_list[0][1]
                move_type = data_list[0][2]
                date_sync = data_list[0][3]
                date_insert = data_list[0][13]

                existing_receipt = self.env['stock.picking'].search([('vit_trxid', '=', doc_number)])
                if existing_receipt:
                    continue

                operation_type_search = self.env['stock.picking.type'].search([('name', '=', 'Goods Issue')])
                location_id = self.env['stock.location'].search([('complete_name', '=', "WH/Stock")], limit=1)

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[4])])]
                registered_products = [data for data in data_list if data[4] and self.env['product.product'].search([('default_code', '=', data[4])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[4] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"GI tidak bisa terbuat karena produk tidak terdaftar\n"
                        error_description += "\n".join([f"- {item_code}" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Goods Issue',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })
                        insert_log_note_query = f"""
                            INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                            VALUES ('Goods Issue', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', GETDATE(), GETDATE());
                        """
                        cursor.execute(insert_log_note_query)
                        conn.commit()

                        update_sync_flag_query = f"""
                            UPDATE t_gi_h
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';

                            UPDATE t_gi_d
                            SET sync_flag = 0,
                                sync_desc = '{error_description}'
                            WHERE doc_number = '{doc_number}';
                        """
                        cursor.execute(update_sync_flag_query)
                        conn.commit()
                else:
                    stock_move = []
                    for data in registered_products:
                        item_code = data[4]
                        qty = float(data[5])
                        doc_num_detail = data[11]
                        line_number_detail = data[12]
                        source_loc = self.env['stock.location'].search([('complete_name', '=', "Virtual Locations/Inventory adjustment")], limit=1)

                        # Add lines to the Goods Issue
                        product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                        if product:
                            insert_t_gi_d_log_query = f"""
                                INSERT INTO t_gi_d_log (doc_number, line_number, item_code, qty, date_insert, date_sync, sync_flag, sync_desc)
                                VALUES ('{doc_num_detail}', '{line_number_detail}', '{item_code}', '{qty}', '{date_insert}', GETDATE(), 1, NULL);
                            """
                            cursor.execute(insert_t_gi_d_log_query)
                            conn.commit()

                            details_gi = (0, 0, {
                                'product_id': product.id,
                                'product_uom_qty': qty,
                                'quantity': qty,
                                'name': product.name,
                                'location_id': location_id.id,
                                'location_dest_id': source_loc.id,
                            })
                            stock_move.append(details_gi)

                    source_loc_form = self.env['stock.location'].search([('complete_name', '=', "Virtual Locations/Inventory adjustment")], limit=1)
                    issue = self.env['stock.picking'].create({
                        'partner_id': False,  # Set the appropriate partner_id
                        'picking_type_id': operation_type_search.id,
                        'location_id': location_id.id,
                        'location_dest_id': source_loc_form.id,
                        'scheduled_date': date_sync,
                        'vit_trxid': doc_number,
                        'vit_type': move_type,
                        'move_ids_without_package': stock_move
                    })

                    update_sync_flag_registered_query = f"""
                        UPDATE t_gi_h
                        SET sync_flag = 1,
                            sync_desc = NULL
                        WHERE doc_number = '{doc_number}';

                        UPDATE t_gi_d
                        SET sync_flag = 1,
                            sync_desc = NULL
                        WHERE doc_number = '{doc_number}';
                    """
                    cursor.execute(update_sync_flag_registered_query)
                    conn.commit()

                    insert_t_gi_h_log_query = f"""
                        INSERT INTO t_gi_h_log (doc_number, move_type, date_doc, date_insert, date_sync, sync_flag, sync_desc)
                        VALUES ('{doc_number}', '{move_type}', '{date_doc}', '{date_insert}', GETDATE(), 1, NULL);
                    """
                    cursor.execute(insert_t_gi_h_log_query)
                    conn.commit()
                    
                    batch.append(issue)
                    order_count += 1

                    if order_count >= batch_size:
                        self.confirm_issue_batch(batch, date_sync, move_type)
                        batch = []

            if batch:
                self.confirm_issue_batch(batch, date_sync, move_type)
                
            delete_query_value_null = f"""
                DELETE FROM t_gi_h
                WHERE sync_flag = 1;

                DELETE FROM t_gi_d
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
    def Searching_GoodsIssue(self, date_from, date_to):
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
                    CONVERT(VARCHAR, h.date_doc, 23) as date_doc,
                    h.move_type,
                    CONVERT(VARCHAR, h.date_sync, 23) as date_sync,
                    d.item_code,
                    d.qty,
                    h.sync_flag,
                    CONVERT(VARCHAR, d.date_sync, 23) as date_sync,
                    d.sync_flag,
                    h.sync_desc,
                    d.sync_desc,
                    d.doc_number,
                    d.line_number
                FROM
                    t_gi_h h
                INNER JOIN
                    t_gi_d d ON h.doc_number = d.doc_number
                WHERE 
                    h.date_doc BETWEEN %s AND %s
                    AND h.sync_flag = 0;
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