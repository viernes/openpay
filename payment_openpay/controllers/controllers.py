# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import werkzeug


class PaymentOpenpay(http.Controller):

    @http.route([
        '/shop/openpay/'
    ], type='http', auth='public', csrf=False, website=True)
    def payment_method(self, **kwargs):
        acquirer = request.env['payment.acquirer'].search([('website_published', '=', True),
                                                            ('registration_view_template_id', '!=', False),
                                                            ('openpay_id','=', kwargs.get('openpay_id'))
                                                            ], limit=1)
        if kwargs.get('pid'):
            partner_id = request.env['res.partner'].browse(int(kwargs['pid']))
            kwargs.update({
                'openpay_apikey': acquirer.openpay_apikey,
                'openpay_environment': 'true' if acquirer.environment else 'false',
                'email': partner_id.email,
                'holder_name': partner_id.name,
                'telephone': partner_id.mobile,
            })
        return request.render("payment_openpay.openpay_payment_s2s_form", kwargs)

    @http.route([
        '/shop/openpay/validation'
    ], type='http', auth='public', csrf=False, website=True, methods=['POST'])
    def validate(self, **kwargs):
        acquirer = request.env['payment.acquirer'].search([('openpay_id','=',kwargs.get('openpay_id'))])
        transaction = request.env['payment.transaction'].search([('reference', '=', kwargs['reference'])], limit=1)
        kwargs.update({
            'partner_id':transaction.partner_id.id
        })
        kwargs.update(acquirer.s2s_process(kwargs))
        transaction.sudo().form_feedback(kwargs, 'openpay')
        return werkzeug.utils.redirect(kwargs.get('return_url', '/shop/checkout'))