from odoo import models, fields, _, api, exceptions

class CustomCOA(models.Model):
    _inherit = 'account.account'

    vit_move_type_1 = fields.Char(string="Move Type 1")
    vit_move_type_2 = fields.Char(string="Move Type 2")