import pymssql
from odoo import models, fields, api, _

class CancelPayment(models.Model):
    _inherit = 'account.payment'

    def cancel_payment(self):
        # Daftar vit_docnum yang ingin Anda cari
        vit_docnums = [
            'INV/PRD/24/02/09/3505',
            'INV/PRD/24/02/15/3921',
            'INV/PRD/24/02/15/3923',
            'INV/PRD/24/02/17/4113',
            'INV/PRD/24/02/18/4177',
            'INV/PRD/24/02/27/4944',
            'INV/PRD/24/02/27/4992',
            'INV/PRD/24/02/28/5060',
            'INV/PRD/24/02/29/5119',
            'INV/PRD/24/02/29/5121',
            'INV/PRD/24/02/29/5129',
            'INV/PRD/24/02/29/5131',
            'INV/PRD/24/03/01/5176',
            'INV/PRD/24/03/02/5218',
            'INV/PRD/24/03/02/5223',
            'INV/PRD/24/03/02/5238',
            'INV/PRD/24/03/03/5287',
            'INV/PRD/24/03/03/5312',
            'INV/PRD/24/03/03/5314',
            'INV/PRD/24/03/03/5317',
            'INV/PRD/24/03/05/5468',
            'INV/PRD/24/02/18/4175',
            'INV/PRD/24/02/19/4303',
            'INV/PRD/24/02/21/4467',
            'INV/PRD/24/02/24/4733',
            'INV/PRD/24/02/28/5048',
            'INV/PRD/24/02/28/5053',
            'INV/PRD/24/03/02/5196',
            'INV/PRD/24/03/03/5270',
            'INV/PRD/24/03/03/5271',
            'INV/PRD/24/03/03/5272',
            'INV/PRD/24/03/03/5273',
            'INV/PRD/24/03/03/5275',
            'INV/PRD/24/03/03/5286',
            'INV/PRD/24/03/03/5311',
            'INV/PRD/24/03/04/5360',
            'INV/PRD/24/03/04/5361',
            'INV/PRD/24/03/04/5362',
            'INV/PRD/24/03/04/5386',
            'INV/PRD/24/03/04/5389',
            'INV/PRD/24/03/05/5446',
            'INV/PRD/24/03/06/5534',
            'INV/PRD/24/03/06/5535',
            'INV/PRD/24/03/06/5537',
            'INV/PRD/24/03/06/5550'
        ]

        # Mencari pembayaran yang memiliki vit_docnum dalam daftar yang diberikan
        payments_to_cancel = self.env['account.payment'].search([('vit_docnum', 'in', vit_docnums)])

        # Membatalkan setiap pembayaran yang ditemukan
        for payment in payments_to_cancel:
            payment.action_draft()
            payment.action_cancel()