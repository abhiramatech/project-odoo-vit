from odoo import models, fields, api

class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    vit_customer_code = fields.Char(string="Customer/Vendor Code")
