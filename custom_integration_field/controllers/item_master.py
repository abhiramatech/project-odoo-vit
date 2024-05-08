import pymssql
from odoo import models, fields, api, _
from datetime import datetime

class IntegrationItem(models.Model):
    _inherit = 'product.template'

    def create_or_update_product(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    item_code,
                    name,
                    item_group,
                    type,
                    sales_price,
                    date_insert,
                    date_sync
                FROM
                    m_product
            """
            cursor.execute(query)
            sql_data = cursor.fetchall()

            for data in sql_data:
                existing_product = self.env['product.template'].search(['|', ('name', '=', data[1]), ('default_code', '=', data[0])], limit=1)
                
                type_mapping = {
                    'Consumable': 'consu',
                    'Storable Product': 'product',
                    'Service': 'service',
                }

                # Determine the category based on detailed_type
                category_name = ''
                if data[3] in type_mapping:
                    category_name = type_mapping[data[3]]
                
                product_categories = self.env['product.category'].search([('name', '=', data[2])])

                # Check if the product already exists
                if not existing_product:
                    self.env['product.template'].create({
                        'name': data[1],
                        'detailed_type': type_mapping.get(data[3], ''),
                        'categ_id': product_categories.id,
                        'invoice_policy': 'order',
                        'list_price': data[4],
                        'default_code': data[0],
                    })
                    insert_m_product_log_query = """
                        INSERT INTO m_product_log (item_code, name, item_group, type, sales_price, date_insert, date_sync, sync_flag)
                        VALUES (%s, %s, %s, %s, %s, GETDATE(), GETDATE(), 1);
                    """
                    cursor.execute(insert_m_product_log_query, (data[0], data[1], data[2], data[3], data[4]))

                    update_query = """
                        UPDATE m_product
                        SET date_sync = %s,
                            sync_flag = 1
                        WHERE item_code = %s;
                    """
                    cursor.execute(update_query, (datetime.now(), data[0]))

                    delete_query_value_null = f"""
                        DELETE FROM m_product
                        WHERE sync_flag = 1;
                    """
                    cursor.execute(delete_query_value_null)
                    conn.commit()
                
                else:
                    existing_product.write({
                        'name': data[1],
                        'detailed_type': type_mapping.get(data[3], ''),
                        'categ_id': product_categories.id,
                        'invoice_policy': 'order',
                        'list_price': data[4],
                        'default_code': data[0],
                    })

                    update_query = """
                        UPDATE m_product
                        SET date_sync = %s,
                            sync_flag = 1
                        WHERE item_code = %s;
                    """
                    cursor.execute(update_query, (datetime.now(), data[0]))
                    
                    # Update m_customer_log table
                    update_customer_log_query = """
                        UPDATE m_product_log
                        SET item_code = %s,
                            name = %s,
                            item_group = %s,
                            type = %s,
                            sales_price = %s,
                            date_sync = %s,
                            date_insert = %s,
                            sync_flag = 1
                        WHERE item_code = %s OR name = %s;
                    """
                    cursor.execute(update_customer_log_query, (data[0], data[1], data[2], data[3],data[4], datetime.now(), datetime.now(), data[0], data[1]))
                    
                    delete_query_value_null = f"""
                        DELETE FROM m_product
                        WHERE sync_flag = 1;
                    """
                    cursor.execute(delete_query_value_null)
                    conn.commit()

            conn.commit()

            
            self.env.cr.commit()

        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error syncing data from SQL Server to Odoo: {error_message}")
        
    @api.model
    def Searching_ItemMaster(self, tanggal_from, tanggal_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                port=1433,
                                database='prado_odoo_prod', 
                                user='prdspradm', 
                                password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    item_code,
                    name,
                    item_group,
                    type,
                    sales_price,
                    date_insert,
                    date_sync
                FROM
                    m_product
            """
            cursor.execute(query,)
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
