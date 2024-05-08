import json
import random
import urllib.request

# Detail instance Odoo pertama
url1 = 'http://192.168.1.161:8069/jsonrpc'
db1 = 'odoolocalhost'
username1 = 'admin'
password1 = 'admin'

# Detail instance Odoo kedua
url2 = 'https://abhiramatech-johan-testing-demo-johan-testing-12741756.dev.odoo.com/jsonrpc'
db2 = 'abhiramatech-johan-testing-demo-johan-testing-12741756'
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

# Autentikasi dan mendapatkan uid untuk instance Odoo pertama
uid1 = call_odoo(url1, 'common', 'authenticate', db1, username1, password1, {})

# Autentikasi dan mendapatkan uid untuk instance Odoo kedua
uid2 = call_odoo(url2, 'common', 'authenticate', db2, username2, password2, {})

# Ambil data dari instance Odoo pertama
data1 = call_odoo(url1, 'object', 'execute_kw', db1, uid1, password1, 'res.partner', 'search_read', [[]], {'fields': ['name', 'phone', 'email']})

# Kirim data ke instance Odoo kedua
for record in data1:
    call_odoo(url2, 'object', 'execute_kw', db2, uid2, password2, 'res.partner', 'create', [record])
    print(f"Data yang masuk: {record}")