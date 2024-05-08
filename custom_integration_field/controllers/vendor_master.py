import pymssql
import threading
from odoo import models, fields, api, _
from datetime import datetime

class IntegrationVendor(models.Model):
    _inherit = 'res.partner'

    def create_vendor(self):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                   port=1433,
                                   database='prado_odoo_prod', 
                                   user='prdspradm', 
                                   password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    code,
                    name,
                    phone,
                    email,
                    address,
                    date_insert,
                    date_sync
                FROM
                    m_vendor
            """
            cursor.execute(query)
            sql_data = cursor.fetchall()

            for data in sql_data:
                existing_vendor = self.env['res.partner'].search(['|', ('name', '=', data[1]), ('vit_customer_code', '=', data[0]), ('supplier_rank', '=', 1)], limit=1)
                if not existing_vendor:
                    # If not exist, create a new one
                    self.env['res.partner'].create({
                        'name': data[1],
                        'street': data[4],
                        'phone': data[2],
                        'email': data[3],
                        'vit_customer_code': data[0],
                        'supplier_rank': 1,
                    })
                    update_query = """
                        UPDATE m_vendor
                        SET date_sync = %s,
                            sync_flag = 1
                        WHERE code = %s;
                    """
                    cursor.execute(update_query, (datetime.now(), data[0]))
                    conn.commit()

                    insert_m_vendor_log_query = """
                        INSERT INTO m_vendor_log (code, name, phone, email, address, date_insert, date_sync, sync_flag, sync_desc)
                        VALUES (%s, %s, %s, %s, %s, GETDATE(), GETDATE(), 1, NULL);
                    """
                    cursor.execute(insert_m_vendor_log_query, (data[0], data[1], data[2], data[3], data[4]))
                    conn.commit()

                    delete_query_value_null = f"""
                        DELETE FROM m_vendor
                        WHERE sync_flag = 1;
                    """
                    cursor.execute(delete_query_value_null)
                    conn.commit()
                
                else:              
                    existing_vendor.write({
                        'name': data[1],
                        'street': data[4],
                        'phone': data[2],
                        'email': data[3],
                        'vit_customer_code': data[0],
                        'supplier_rank': 1,
                    })

                    update_query = """
                        UPDATE m_vendor
                        SET date_sync = %s,
                            sync_flag = 1
                        WHERE code = %s;
                    """
                    cursor.execute(update_query, (datetime.now(), data[0]))
                    conn.commit()

                    update_query_log = """
                        UPDATE m_vendor_log
                        SET name = %s,
                            code = %s,
                            phone = %s,
                            email = %s,
                            address = %s,
                            date_sync = %s,
                            sync_flag = 1
                        WHERE code = %s
                        OR name = %s;
                    """
                    cursor.execute(update_query_log, (data[1], data[0], data[2], data[3], data[4], datetime.now(), data[0], data[1]))
                    conn.commit()

                    delete_query_value_null = f"""
                        DELETE FROM m_vendor
                        WHERE sync_flag = 1;
                    """
                    cursor.execute(delete_query_value_null)
                    conn.commit()

            self.env.cr.commit()
        except pymssql.Error as e:
            # Handle the exception or log the error message
            error_message = str(e)
            # Add your error handling logic here
            raise ValueError(f"Error syncing data from SQL Server to Odoo: {error_message}")
        
    @api.model
    def Searching_VendorMaster(self, tanggal_from, tanggal_to):
        try:
            conn = pymssql.connect(server='pradovet.database.windows.net',
                                port=1433,
                                database='prado_odoo_prod', 
                                user='prdspradm', 
                                password='*112233*Sunter*')
            cursor = conn.cursor()

            query = """
                SELECT
                    code,
                    name,
                    phone,
                    email,
                    address,
                    date_insert,
                    date_sync
                FROM
                    m_vendor
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
