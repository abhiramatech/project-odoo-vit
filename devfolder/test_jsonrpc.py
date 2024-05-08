import json
import random
import urllib.request
import pymssql

def conf_sql_data():
    # Koneksi ke database SQL
    conn = pymssql.connect(server='116.254.101.239',
                           port=53132,
                           database='test_integration',
                           user='sa',
                           password='P@ssw0rd')
    cursor = conn.cursor()

    query = """
        SELECT
            customer_code
        FROM
            t_inv_h
    """
    cursor.execute(query)
    sql_data = cursor.fetchall()

    # Detail instance Odoo
    url2 = 'https://abhiramatech-testing-integration-test-integration-12940739.dev.odoo.com/jsonrpc'
    db2 = 'https://abhiramatech-testing-integration-test-integration-12940739'
    username2 = 'admin'
    password2 = 'admin'

    def call_odoo(url, service, method, *args):
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'service': service,
                'method': method,
                'args': args,
            },
            'id': random.randint(0, 1000000000),
        }
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data, headers)
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('error'):
                raise Exception(result['error'])
            return result['result']

    # Autentikasi dan mendapatkan uid untuk instance Odoo
    uid2 = call_odoo(url2, 'common', 'authenticate', db2, username2, password2, {})

    for data in sql_data:
        customer_code = data[0]

        vals_data = {
            'name': customer_code,
            'customer_code': customer_code
        }

        # Membuat record baru di Odoo menggunakan data dari SQL
        call_odoo(url2, 'object', 'execute_kw', db2, uid2, password2, 'res.partner', 'create', [vals_data])
        print(f"Data yang dimasukkan: {vals_data}")