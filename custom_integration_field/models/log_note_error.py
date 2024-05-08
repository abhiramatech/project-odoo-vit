from odoo import models, fields, api
import re
from datetime import datetime
import requests
import pymssql

class LogNoteError(models.Model):
    _name = 'log.note.error'
    _description = 'Log Note Error From Scheduler'

    vit_doc_type = fields.Char(string='Document Type')
    vit_jubelio_key = fields.Char(string='Document Number')
    vit_sync_trx_date = fields.Date(string='Transaction Date')
    vit_sync_status = fields.Char(string='Status')
    vit_sync_desc = fields.Char(string='Description')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)

    def extract_invoice_number(self, description):
        # Ensure that description is a string
        if not isinstance(description, str):
            description = str(description)

        # Use regular expression to extract the invoice number from description
        match = re.search(r'invoice (\S+) dalam', description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def extract_journal_payment(self, description):
        # Ensure that description is a string
        if not isinstance(description, str):
            description = str(description)

        # Use regular expression to extract the invoice number from description
        match = re.search(r'dikarenakan (\S+) tidak ', description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def extract_payment_CN_number(self, description):
        # Ensure that description is a string
        if not isinstance(description, str):
            description = str(description)

        # Use regular expression to extract the invoice number from description
        match = re.search(r'invoice (\S+) dalam', description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def remove_successful_transactions(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()

            # Hapus data yang sesuai dengan kondisi dari tabel Azure SQL
            # Sales Order
            error_so = self.env['log.note.error'].search([('vit_doc_type', '=', 'Sales Order')])
            for res in error_so:
                matching_saleorder = self.env['sale.order'].search([('vit_trxid', '=', res.vit_jubelio_key)])
                if matching_saleorder:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (res.vit_jubelio_key,))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (res.vit_jubelio_key,))
                        conn.commit()
                    # Setelah memastikan, baru hapus dari log.note.error
                    res.unlink()
                    conn.commit()


            # Payment Invoice
            error_payment_inv = self.env['log.note.error'].search([('vit_doc_type', '=', 'Payment Invoice')])
            for errors_payment_inv in error_payment_inv:
                matching_accountpayment = self.env['account.payment'].search([('vit_docnum', '=', self.extract_invoice_number(errors_payment_inv.vit_sync_desc))])
                if matching_accountpayment:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (self.extract_invoice_number(errors_payment_inv.vit_sync_desc),))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (self.extract_invoice_number(errors_payment_inv.vit_sync_desc),))
                        conn.commit()
                    errors_payment_inv.unlink()
                    conn.commit()

            error_payment_inv_journals = self.env['log.note.error'].search([('vit_doc_type', '=', 'Payment Invoice')])
            for error_payment_inv_journal in error_payment_inv_journals:
                matching_accountpayment_journal = self.env['account.payment'].search([('vit_trxid', '=', error_payment_inv_journal.vit_jubelio_key)])
                if matching_accountpayment_journal:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (error_payment_inv_journal.vit_jubelio_ke,))
                    existing_doc_payment_journal = cursor.fetchone()
                    if existing_doc_payment_journal:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (error_payment_inv_journal.vit_jubelio_ke,))
                        conn.commit()
                    error_payment_inv_journal.unlink()

            # Credit Note
            error_credit_note = self.env['log.note.error'].search([('vit_doc_type', '=', 'Credit Note')])
            for rec in error_credit_note:
                matching_accountmove = self.env['account.move'].search([('vit_trxid', '=', rec.vit_jubelio_key)])
                if matching_accountmove:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (rec.vit_jubelio_key,))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (rec.vit_jubelio_key,))
                        conn.commit()
                    rec.unlink()
                    conn.commit()

            # Payment Credit Note
            error_pcn = self.env['log.note.error'].search([('vit_doc_type', '=', 'Payment Credit Note')])
            for errors_pcn in error_pcn:
                matching_payment_cn = self.env['account.payment'].search([('vit_trxid', '=', self.extract_payment_CN_number(errors_pcn.vit_sync_desc))])
                if matching_payment_cn:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (self.extract_payment_CN_number(errors_pcn.vit_sync_desc),))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (self.extract_payment_CN_number(errors_pcn.vit_sync_desc),))
                        conn.commit()
                    errors_pcn.unlink()
                    conn.commit()

            # Purchase Order
            error_PO = self.env['log.note.error'].search([('vit_doc_type', '=', 'Purchase Order')])
            for errors_PO in error_PO:
                matching_purchaseorder = self.env['purchase.order'].search([('vit_trxid', '=', errors_PO.vit_jubelio_key)])
                if matching_purchaseorder:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (errors_PO.vit_jubelio_key,))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (errors_PO.vit_jubelio_key,))
                        conn.commit()
                    errors_PO.unlink()
                    conn.commit()

            # Goods Receipt
            error_GR = self.env['log.note.error'].search([('vit_doc_type', '=', 'Goods Receipt')])
            for errors_GR in error_GR:
                matching_goodsreceipt = self.env['stock.picking'].search([('vit_trxid', '=', errors_GR.vit_jubelio_key)])
                if matching_goodsreceipt:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (errors_GR.vit_jubelio_key,))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (errors_GR.vit_jubelio_key,))
                        conn.commit()
                    errors_GR.unlink()
                    conn.commit()

            # Goods Issue
            error_GI = self.env['log.note.error'].search([('vit_doc_type', '=', 'Goods Issue')])
            for errors_GI in error_GI:
                matching_goodsissue = self.env['stock.picking'].search([('vit_trxid', '=', errors_GI.vit_jubelio_key)])
                if matching_goodsissue:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (errors_GI.vit_jubelio_key,))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (errors_GI.vit_jubelio_key,))
                        conn.commit()
                    errors_GI.unlink()
                    conn.commit()

            # Return To Vendor
            error_rtv = self.env['log.note.error'].search([('vit_doc_type', '=', 'Return To Vendor')])
            for errors_rtv in error_rtv:
                matching_returnvendor = self.env['stock.picking'].search([('vit_trxid', '=', errors_rtv.vit_jubelio_key)])
                if matching_returnvendor:
                    cursor.execute("SELECT doc_number FROM t_log_note WHERE doc_number = %s", (errors_rtv.vit_jubelio_key,))
                    existing_doc = cursor.fetchone()
                    if existing_doc:
                        cursor.execute("DELETE FROM t_log_note WHERE doc_number = %s", (errors_rtv.vit_jubelio_key,))
                        conn.commit()
                    errors_rtv.unlink()
                    conn.commit()

        except Exception as e:
            # Tangani pengecualian atau log pesan kesalahan jika diperlukan
            print("Error occurred:", e)
        finally:
            # Tutup koneksi setelah selesai
            conn.close()