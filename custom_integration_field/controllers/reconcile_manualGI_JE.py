import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
from collections import defaultdict
import time
import pymssql

class IntegrationGoodsReceipt(models.Model):
    _inherit = 'stock.picking'

    def Manual_Reconcile_GI_JE(self):
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
                    h.move_type = 'StockTake';
            """

            cursor.execute(query)
            sql_data = cursor.fetchall()

            for res in sql_data:
                move_type = res[2]

                goods_receipts = self.env['stock.picking'].search([('state', 'in', ('assigned', 'confirmed')), ('picking_type_id.name', '=', 'Goods Issue')])

                for goods_receipt in goods_receipts:
                    goods_receipt.action_confirm()
                    goods_receipt.button_validate()

                    find_journal = self.env['account.move'].search([('ref', 'ilike',goods_receipt.name)])
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
        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error connecting to SQL Server: {error_message}")