import pymssql
from odoo import models, fields, api, _

class ManualIntegrationPaymentCreditNote(models.Model):
    _inherit = 'account.move'
        
    # --------------------------------------------------------------------------------------- #
        #                           MANUAL PAYMENT CREDITNOTE                 #
        
    @api.model
    def Searching_PaymentCreditNote(self, date_from, date_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                port=1433,
                                database='prado_odoo_prod', 
                                user='prdspradm', 
                                password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    p.doc_number,
                    p.customer_code,
                    p.ref_id,
                    p.amount,
                    p.payment_method,
                    p.date_doc,
                    p.sync_flag,
                    p.sync_desc
                FROM
                    t_pay_ref p
                WHERE
                    p.date_doc BETWEEN %s AND %s
                    AND (p.sync_flag = 0 OR p.sync_flag IS NULL);
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

    @api.model
    def Manual_Sync_PaymentCreditNote_Integration(self, date_from, date_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    p.doc_number,
                    p.customer_code,
                    p.ref_id,
                    p.amount,
                    p.payment_method,
                    p.date_doc
                FROM
                    t_pay_ref p
                WHERE 
                    p.date_doc BETWEEN %s AND %s
                    AND (p.sync_flag = 0 OR p.sync_flag IS NULL);
            """
            cursor.execute(query, (date_from, date_to))
            sql_data = cursor.fetchall()

            # Set the chunk size to the length of the sql_data
            chunk_size = 50
            LogError = self.env['log.note.error']

            for i in range(0, len(sql_data), chunk_size):
                chunk = sql_data[i:i + chunk_size]

                for data in chunk:
                    doc_number = data[0]
                    customer_code = data[1]
                    ref_id = data[2]
                    amount = data[3]
                    payment_method = data[4]
                    date_doc = data[5]
                    
                    find_journal = self.env['account.journal'].search([('name', '=', payment_method)])
                    if find_journal:
                        existing_payment = self.env['account.payment'].search([('vit_trxid', '=', doc_number)])
                        if not existing_payment:
                            find_invoice = self.env['account.move'].search([('vit_trxid', '=', doc_number), ('payment_state', 'in', ('not_paid', 'partial')), ('state', '=', 'posted'), ('move_type', '=', 'out_refund')])
                            if find_invoice:
                                payment_register = self.env['account.payment.register'].with_context(
                                    active_model='account.move', active_ids=find_invoice.ids
                                ).create({
                                    'payment_date': date_doc,
                                    'amount': amount,
                                    'journal_id': find_journal.id,
                                    'vit_trxid': doc_number,
                                    'vit_docnum': ref_id,
                                })
                                payment_register.action_create_payments()
                                update_sync_flag_query = f"""
                                    UPDATE t_pay_ref
                                    SET sync_flag = 1
                                    WHERE doc_number = '{doc_number}';
                                """
                                cursor.execute(update_sync_flag_query)
                                conn.commit()

                                insert_t_pay_ref_log_query = f"""
                                    INSERT INTO t_pay_ref_log (doc_number, customer_code, ref_id, amount, payment_method, date_doc, date_sync, sync_flag, sync_desc)
                                    VALUES ('{doc_number}', '{customer_code}', '{ref_id}', '{amount}', '{payment_method}', '{date_doc}', GETDATE(), 1, NULL);
                                """
                                cursor.execute(insert_t_pay_ref_log_query)
                                conn.commit()
                                
                            else:
                                existing_log_error = LogError.search([('vit_jubelio_key', '=', doc_number)])
                                if not existing_log_error:
                                    error_description = f"Tidak ditemukan invoice {doc_number} dalam dokumen payment"
                                    LogError.create({
                                        'vit_doc_type': 'Payment Credit Note',
                                        'vit_jubelio_key': doc_number,
                                        'vit_sync_trx_date': date_doc,
                                        'vit_sync_status': 'Failed',
                                        'vit_sync_desc': error_description,
                                    })
                                    insert_log_note_query = f"""
                                        INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                                        VALUES ('Payment Credit Note', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', GETDATE(), GETDATE());
                                    """
                                    cursor.execute(insert_log_note_query)
                                    conn.commit()

                                    update_sync_flag_query = f"""
                                        UPDATE t_pay_ref
                                        SET sync_flag = 0
                                            sync_desc = '{error_description}'
                                        WHERE doc_number = '{doc_number}';
                                    """
                                    cursor.execute(update_sync_flag_query)
                                    conn.commit()
                    else:
                        existing_log_error = LogError.search([('vit_jubelio_key', '=', doc_number)])
                        if not existing_log_error:
                            error_message = f"Payment tidak bisa dibuat dikarenakan {payment_method} tidak terdaftar"
                            LogError.create({
                                'vit_doc_type': 'Payment Credit Note',
                                'vit_jubelio_key': doc_number,
                                'vit_sync_trx_date': date_doc,
                                'vit_sync_status': 'Failed',
                                'vit_sync_desc': error_message,
                            })
                            insert_log_note_query = f"""
                                INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                                VALUES ('Payment Credit Note', '{doc_number}', '{date_doc}', 'Failed', '{error_message}', GETDATE(), GETDATE());
                            """
                            cursor.execute(insert_log_note_query)
                            conn.commit()

                            update_sync_flag_query = f"""
                                UPDATE t_pay_ref
                                SET sync_flag = 0
                                    sync_desc = '{error_message}'
                                WHERE doc_number = '{doc_number}';
                            """
                            cursor.execute(update_sync_flag_query)
                            conn.commit()
                            
            delete_query_value_null = f"""
                DELETE FROM t_pay_ref
                WHERE sync_flag = 1;

                DELETE FROM t_pay_ref
                WHERE sync_flag = 1;
            """
            cursor.execute(delete_query_value_null)
            conn.commit()
        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error syncing data from SQL Server to Odoo: {error_message}")
