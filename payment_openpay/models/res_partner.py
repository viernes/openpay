# coding: utf-8
import openpay

from odoo import api, fields, models, _

class AcquirerOpenpay(models.Model):
    _name = 'openpay.partner'

    name = fields.Many2one('res.partner', required=True)
    openpay_id = fields.Char('Name', required=True)

    def get_openpay_id(self, partner_id):
        return self.search([('name','=', partner_id)], limit = 1).openpay_id