from odoo import models, fields, _, api
from odoo.exceptions import UserError
import pymssql
from datetime import datetime

class SpecialSycnIntegratiion(models.Model):
    _name = 'special.sync'
    _description = 'Special Sync For Integration'

    # invoice_num = fields.Char(string='Invoice Number')
    tanggal_from = fields.Date(string='Date From')
    tanggal_to = fields.Date(string='Date To')
    # model_sync = fields.Many2one('ir.model', string='Model')
    sync_model = fields.Selection([('sale order', 'Sale Order'), 
                                   ('validate delivery', 'Validate Delivery'),
                                   ('invoice', 'Invoice'),
                                   ('payment invoice', 'Payment Invoice'), 
                                   ('credit note', 'Credit Note'), 
                                   ('return order', 'Return Order'),
                                   ('payment credit note', 'Payment Credit Note'),
                                   ('purchase order', 'Purchase Order'),
                                   ('bill purchase order', 'Bill Purchase Order'),
                                   ('goods return', 'Goods Return'), 
                                   ('goods issue', 'Goods Issue'),
                                   ('goods receipt', 'Goods Receipt'),
                                   ('vendor master', 'Vendor Master'),
                                   ('item master', 'Item Master'),
                                   ('customer master', 'Customer Master'),
                                   ('clear log note', 'Clear Log Note')], string='Modul To Sync')
    
    special_sync_ids = fields.One2many('special.sync.line', 'special_sync_id', string='Special Sync Ids', readonly=True)

    def action_search(self):
        if self.tanggal_from and self.tanggal_to:
                tanggal_from = self.tanggal_from.strftime('%Y-%m-%d')
                tanggal_to = self.tanggal_to.strftime('%Y-%m-%d')
        else:
            raise UserError(_("Mohon untuk mengisi 'Tanggal From' and 'Tanggal To' untuk melanjutkan!!."))

        # Ambil sync_model yang dipilih
        sync_model = self.sync_model

        if not self.sync_model:
            raise UserError(_("Mohon untuk mengisi 'Modul To Sync' sebelum mencari!!."))
        

        if sync_model == 'sale order':
            self.special_sync_ids.unlink()
            invoices_sales_data = self.env['sale.order'].Searching_InvoicesSales(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            next_no_inc = 1
            # Initialize a set to track document numbers
            existing_doc_nums = set()

            # Iterate through the data
            for data in invoices_sales_data:
                # Check if the doc_num already exists in the set
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[2], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[5],  
                    }))
                    next_no_inc += 1

                    # Add the doc_num to the set to avoid duplicates
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'payment invoice':
            self.special_sync_ids.unlink()
            payment_invoice_data = self.env['account.move'].Searching_PaymentInvoice(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in payment_invoice_data:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[5], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[6],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'credit note':
            self.special_sync_ids.unlink()
            credit_note = self.env['account.move'].Searching_CreditNote(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in credit_note:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[3], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[10],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'return order':
            self.special_sync_ids.unlink()
            return_order = self.env['stock.picking'].Searching_ReturnOrder(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in return_order:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[3], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[10],   
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'payment credit note':
            self.special_sync_ids.unlink()
            payment_credit_note_data = self.env['account.move'].Searching_PaymentCreditNote(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in payment_credit_note_data:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[5], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[7],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'purchase order':
            self.special_sync_ids.unlink()
            purchase_order = self.env['purchase.order'].Searching_PurchaseOrder(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in purchase_order:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[3], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[6],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'goods return':
            self.special_sync_ids.unlink()
            return_vendor = self.env['stock.picking'].Searching_ReturnVendor(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in return_vendor:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[3], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[4],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'goods issue':
            self.special_sync_ids.unlink()
            goods_issue = self.env['stock.picking'].Searching_GoodsIssue(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in goods_issue:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[1], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[9],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'goods receipt':
            self.special_sync_ids.unlink()
            goods_receipt = self.env['stock.picking'].Searching_GoodsReceipt(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in goods_receipt:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'sync_date': data[1], 
                        'sync_status': 'Gagal',
                        'sync_desc': data[9],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'vendor master':
            self.special_sync_ids.unlink()
            vendor_master = self.env['res.partner'].Searching_VendorMaster(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in vendor_master:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'name': data[1],
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'customer master':
            self.special_sync_ids.unlink()
            customer_master = self.env['res.partner'].Searching_CustomerMaster(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in customer_master:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'name': data[1],  
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})

        elif sync_model == 'item master':
            self.special_sync_ids.unlink()
            item_master = self.env['product.template'].Searching_ItemMaster(tanggal_from, tanggal_to)

            special_sync_line_obj = self.env['special.sync.line']
            special_sync_lines = []
            existing_doc_nums = set()
            next_no_inc = 1
            for data in item_master:
                if data[0] not in existing_doc_nums:
                    special_sync_lines.append((0, 0, {
                        'no_inc': next_no_inc,
                        'doc_num': data[0],  
                        'name': data[1],
                        'item_group': data[2],
                    }))
                    next_no_inc += 1
                    existing_doc_nums.add(data[0])

            self.write({'special_sync_ids': special_sync_lines})


    def action_export(self):
        if self.sync_model == 'validate delivery':
            self.env['stock.picking'].validate_delivery_orders()
            return
        elif self.sync_model == 'invoice':
            self.env['sale.order'].buat_invoice()
            return
        elif self.sync_model == 'bill purchase order':
            self.env['purchase.order'].create_bills_from_po()
            return
        elif self.sync_model == 'customer master':
            self.env['res.partner'].create_cust()
            return
        elif self.sync_model == 'vendor master':
            self.env['res.partner'].create_vendor()
            return
        elif self.sync_model == 'item master':
            self.env['product.template'].create_or_update_product()
            return
        elif self.sync_model == 'clear log note':
            self.env['log.note.error'].remove_successful_transactions()
            return
        
        if self.tanggal_from and self.tanggal_to:
                tanggal_from = self.tanggal_from.strftime('%Y-%m-%d')
                tanggal_to = self.tanggal_to.strftime('%Y-%m-%d')
        else:
            raise UserError(_("Mohon untuk mengisi 'Tanggal From' and 'Tanggal To' untuk melanjutkan!!."))

        if self.sync_model == 'sale order':
            self.env['sale.order'].Manual_SalesOrder_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'payment invoice':
            self.env['account.move'].Manual_Sync_PaymentInvoice_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'credit note':
            self.env['account.move'].Manual_Sync_CreditNote_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'return order':
            self.env['stock.picking'].Manual_ReturnOrder_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'payment credit note':
            self.env['account.move'].Manual_Sync_PaymentCreditNote_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'purchase order':
            self.env['purchase.order'].Manual_Sync_PurchaseOrder_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'goods return':
            self.env['stock.picking'].Manual_Sync_ReturnVendor_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'goods issue':
            self.env['stock.picking'].Manual_Sync_GoodsIssue_Integration(tanggal_from, tanggal_to)
        elif self.sync_model == 'goods receipt':
            self.env['stock.picking'].Manual_Sync_GoodsReceipt_Integration(tanggal_from, tanggal_to)

class SpecialSyncIntegrationLine(models.Model):
    _name = 'special.sync.line'
    _description = 'Special Sync For Integration'

    special_sync_id = fields.Many2one('special.sync', string='Special Sync Id')
    no_inc = fields.Integer(string='No')
    doc_num = fields.Char(string="Document Number/Code")
    name = fields.Char(string='Name')
    item_group = fields.Char(string='Item Group')
    sync_date = fields.Date(string='Document Date')
    sync_status = fields.Char(string='Status')
    sync_desc = fields.Char(string='Status Description')
