from odoo import models, fields, api
import pymssql
from odoo.exceptions import UserError
from collections import defaultdict

class CustomDOField(models.Model):
    _inherit = 'stock.picking'

    vit_trxid = fields.Char(string="Transaction ID")
    vit_ref = fields.Char(string="Ref Number")
    vit_type = fields.Char(string="Transaction Type")
    vit_is_integrated = fields.Boolean(string="is_integrated")
