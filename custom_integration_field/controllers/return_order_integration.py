import pymssql
from odoo import models, fields, api, _
from collections import defaultdict

class IntegrationReturnOrder(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def ReturnOrder_Integration(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()
            log_error = self.env['log.note.error']

            update_date_sync_query = """
                UPDATE t_cn_h
                SET date_sync = GETDATE();

                UPDATE t_cn_d
                SET date_sync = GETDATE();
            """
            cursor.execute(update_date_sync_query)
            conn.commit()

            query = """
                SELECT
                    h.doc_number,
                    h.customer_code,
                    h.ref_id,
                    h.date_doc,
                    d.item_code,
                    d.item_name,
                    d.quantity,
                    d.price_unit,
                    d.doc_number,
                    d.line_number
                FROM
                    t_cn_h_log h
                INNER JOIN
                    t_cn_d_log d ON h.doc_number = d.doc_number;
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
                existing_receipt = self.env['stock.picking'].search([('vit_trxid', '=', doc_number)])
                if existing_receipt:
                    continue

                operation_type_search = self.env['stock.picking.type'].search([('name', '=', 'Return')])
                location_id = self.env['stock.location'].search([('complete_name', '=', "WH/Stock")], limit=1)

                unregistered_products = [data for data in data_list if not self.env['product.product'].search([('default_code', '=', data[4])])]
                registered_products = [data for data in data_list if data[4] and self.env['product.product'].search([('default_code', '=', data[4])])]

                if unregistered_products:
                    # Log error for products that are not registered
                    products_to_log = [data[4] for data in unregistered_products]

                    existing_error = log_error.search([('vit_jubelio_key', '=', doc_number)])
                    if not existing_error:
                        error_description = f"Retur tidak bisa terbuat karena produk tidak terdaftar\n"
                        error_description += "\n".join([f"Item Code: {item_code}" for item_code in products_to_log])

                        log_error.create({
                            'vit_doc_type': 'Return Order',
                            'vit_jubelio_key': doc_number,
                            'vit_sync_trx_date': date_doc,
                            'vit_sync_status': 'Failed',
                            'vit_sync_desc': error_description,
                        })
                else:
                    partners = self.env['res.partner'].search([('vit_customer_code', '=', customer_code)])
                    stock_move_line = []
                    for data in registered_products:
                        item_code = data[4]
                        item_name = data[5]
                        qty = float(data[6])
                        doc_num_detail = data[8]
                        line_number_detail = data[9]

                        source_loc = self.env['stock.location'].search([('complete_name', '=', "Partners/Customers")], limit=1)
                        product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
                        if product:
                            move_line = (0, 0, {
                                'product_id': product.id,
                                'product_uom_qty': qty,
                                'quantity': qty,
                                'name': product.name,
                                'location_id': source_loc.id,
                                'location_dest_id': location_id.id,
                            })
                            stock_move_line.append(move_line)
                            
                    return_order = self.env['stock.picking'].create({
                        'partner_id': partners.id,  # Set the appropriate partner_id
                        'picking_type_id': operation_type_search.id,
                        'location_id': source_loc.id,
                        'location_dest_id': location_id.id,
                        'scheduled_date': date_doc,
                        'vit_trxid': doc_number,
                        'vit_ref': ref_id,
                        'move_ids_without_package': stock_move_line,
                    })

                    batch.append(return_order)
                    order_count += 1

                    if order_count >= batch_size:
                        self.confirm_retur_order_batch(batch, date_doc)
                        batch = []
                
            if batch:
                self.confirm_retur_order_batch(batch, date_doc)

            delete_query_value_null = f"""
                DELETE FROM t_cn_h
                WHERE sync_flag = 1;

                DELETE FROM t_cn_d
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

    def confirm_retur_order_batch(self, batch, date_doc):
        for receipt in batch:
            receipt.action_confirm()
            receipt.button_validate()