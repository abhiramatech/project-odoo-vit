import pymssql
from odoo import models, fields, api, _

class IntegrationPaymentInvoice(models.Model):
    _inherit = 'account.move'

    @api.model
    def PaymentInvoice_Integration(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()

            update_date_sync_query = """
                UPDATE t_pay_inv
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()

            query = """
                SELECT
                    p.doc_number,
                    p.customer_code,
                    p.ref_id,
                    p.amount,
                    p.payment_method,
                    p.date_doc,
                    p.date_insert
                FROM
                    t_pay_inv p
                WHERE
                    p.payment_method <> 'Utang';
            """
            cursor.execute(query)
            sql_data = cursor.fetchall()

            LogError = self.env['log.note.error']
            payment_count = 0  # Counter for the number of payments made

            updates_to_sync = []
            inserts_to_sync = []

            for data in sql_data:
                if payment_count >= 200:
                    break  # Exit the loop if 400 payments are made
                doc_number = data[0]
                customer_code = data[1]
                ref_id = data[2]
                amount = data[3]
                payment_method = data[4]
                date_doc = data[5]
                date_insert = data[6]
                
                find_journal = self.env['account.journal'].search([('name', '=', payment_method)], limit=1)
                if find_journal:
                    existing_payment = self.env['account.payment'].search([('vit_trxid', '=', doc_number)])
                    if not existing_payment:
                        find_invoice = self.env['account.move'].search([('vit_trxid', '=', ref_id), ('payment_state', 'in', ('not_paid', 'partial')), ('state', '=', 'posted'), ('move_type', '=', 'out_invoice')])
                        if find_invoice:
                            payment_register = self.env['account.payment.register'].with_context(
                                active_model='account.move', active_ids = find_invoice.ids
                            ).create({
                                'payment_date': date_doc,
                                'amount': amount,
                                'journal_id': find_journal.id,
                                'vit_trxid': doc_number,
                                'vit_docnum': ref_id,
                            })
                            payment_register.action_create_payments()

                            updates_to_sync.append((doc_number,))
                            inserts_to_sync.append((doc_number, customer_code, ref_id, amount, payment_method, date_doc, date_insert))
                            payment_count += 1  # Increment the payment count
                        else:
                            existing_log_error = LogError.search([('vit_jubelio_key', '=', doc_number)])
                            if not existing_log_error:
                                error_description = f"Tidak ditemukan invoice {ref_id} dalam dokumen payment {doc_number}"
                                LogError.create({
                                    'vit_doc_type': 'Payment Invoice',
                                    'vit_jubelio_key': doc_number,
                                    'vit_sync_trx_date': date_doc,
                                    'vit_sync_status': 'Failed',
                                    'vit_sync_desc': error_description,
                                })
                                insert_log_note_query = f"""
                                    INSERT INTO t_log_note (doc_type, doc_number, transaction_date, sync_status, sync_desc, date_insert, date_sync)
                                    VALUES ('Payment Invoice', '{doc_number}', '{date_doc}', 'Failed', '{error_description}', GETDATE(), GETDATE());
                                """
                                cursor.execute(insert_log_note_query)
                                conn.commit()

                                update_sync_flag_query = f"""
                                    UPDATE t_pay_inv
                                    SET sync_flag = 0,
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
                            'vit_doc_type': 'Payment Invoice',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_message,
                        })

                        update_sync_flag_query = f"""
                            UPDATE t_pay_inv
                            SET sync_flag = 1
                            WHERE doc_number = '{doc_number}';
                        """
                        cursor.execute(update_sync_flag_query)
                        conn.commit()

            update_sync_flag_query = """
                UPDATE t_pay_inv
                SET sync_flag = 1
                WHERE doc_number = %s;
            """
            cursor.executemany(update_sync_flag_query, updates_to_sync)
            conn.commit()

            # Melakukan penyisipan massal untuk t_pay_inv_log
            insert_t_pay_inv_log_query = """
                INSERT INTO t_pay_inv_log (doc_number, customer_code, ref_id, amount, payment_method, date_doc, date_insert, date_sync, sync_flag, sync_desc)
                VALUES (%s, %s, %s, %s, %s, %s, %s, GETDATE(), 1, NULL);
            """
            cursor.executemany(insert_t_pay_inv_log_query, inserts_to_sync)
            conn.commit()

            delete_query_value_null = f"""
                DELETE FROM t_pay_inv
                WHERE sync_flag = 1;
            """
            cursor.execute(delete_query_value_null)
            conn.commit()
        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error syncing data from SQL Server to Odoo: {error_message}")