# coding: utf-8
import openpay
import json
import logging
import dateutil.parser
from werkzeug import urls
from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

class AcquirerOpenpay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('openpay', 'Openpay')])
    openpay_id = fields.Char('Openpay ID', required_if_provider='openpay')
    openpay_apikey = fields.Char('Openpay ApiKey', required_if_provider='openpay')
    openpay_privatekey = fields.Char('Openpay Private Key', required_if_provider='openpay')

    def _get_feature_support(self):
        res = super(AcquirerOpenpay, self)._get_feature_support()
        res['authorize'].append('openpay')
        res['tokenize'].append('openpay')
        return res

    @api.model
    def _get_openpay_urls(self, environment):
        """ Adyen URLs: yhpp: hosted payment page: pay.shtml for single, select.shtml for multiple """
        return {
            'openpay_form_url': '/shop/openpay/',
        }

    @api.multi
    def openpay_get_form_action_url(self):
        return self._get_openpay_urls(self.environment)['openpay_form_url']

    @api.multi
    def openpay_form_generate_values(self, values={}):
        values.update({
            'openpay_id': self.openpay_id,
        })
        return values

    @api.multi
    def openpay_s2s_form_process(self, kwargs={}):
        get_openpay_id = self.openpay_create_custumer(kwargs)

        try:

            charges = get_openpay_id.charges.create(source_id=kwargs.get('token_id'),
                                              device_session_id=kwargs.get('deviceIdHiddenFieldName'),
                                              method="card",
                                              amount=float(kwargs.get('amount', 0)),
                                              description=kwargs.get('reference', 'Charge'),
                                              capture=True)
        except Exception as e:
            charges = e

        return charges

    @api.model
    def openpay_create_custumer(self, kwargs):
        openpay_partner = self.env['openpay.partner']
        get_openpay_id = openpay_partner.get_openpay_id(kwargs['partner_id'])
        openpay.api_key = self.openpay_privatekey
        openpay.verify_ssl_certs = False
        openpay.merchant_id = self.openpay_id
        openpay.production = True if self.environment == 'prod' else False
        if get_openpay_id:
            return  openpay.Customer.retrieve(get_openpay_id)
        else:
            openpay_id = openpay.Customer.create(
                name=kwargs.get('holder_name'),
                email=kwargs.get('email'),
                phone_number=kwargs.get('telephone')
            )
            openpay_partner.create({
                'name': kwargs['partner_id'],
                'openpay_id': openpay_id.id
            })

            return openpay_id


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    openpay_profile = fields.Char(string='Card', help='This contains the unique reference '
                                    'for this partner/payment token combination in the Authorize.net backend')


    @api.model
    def openpay_create(self, values):
        if values.get('card_number'):
            values['card_number'] = values['card_number'].replace(' ', '')
            openpay_partner = self.env['openpay.partner']
            res =  openpay_partner.get_openpay_id(values.get('partner_id'))
            if res:
                return {
                    'openpay_profile': res,
                    'name': 'XXXXXXXXXXXX%s - %s' % (values['card_number'][-4:], values['holder_name']),
                    'acquirer_ref': values['reference'],
                }
            else:
                raise ValidationError(_('The Customer Profile creation in Authorize.NET failed.'))
        else:
            return values


class TxOpenpay(models.Model):
    _inherit = 'payment.transaction'
    openpay_txn_type = fields.Char('Transaction type')

    def _openpay_form_get_tx_from_data(self, data):
        """
        N_PROGRESS	Transaction is in progress
        COMPLETED	Transaction was succesfully completed
        REFUNDED	Transaction that has been refunded
        CHARGEBACK_PENDING	Transaction that has a pending chargeback
        CHARGEBACK_ACCEPTED	Transaction that has an accepted chargeback
        CHARGEBACK_ADJUSTMENT	Transaction that has an ajust for chargeback
        CHARGE_PENDING	Transaction that is waiting to be paid
        CANCELLED	Transaction that was not paid and has been cancelled
        FAILED	Transaction that was paid but ocurred an error
        :param data:
        :return:
        """
        status = data.get('status')
        res = {
            'acquirer_reference': data.get('reference'),
            'openpay_txn_type': data.get('operation_type'),
        }
        if status in ['completed', 'n_progress']:
            _logger.info('Validated Openpay payment for tx %s: set as done' % (self.reference))
            date_validate = data.get('openration_date', fields.Datetime.now())
            res.update(state='done', date_validate=date_validate)

            if self.partner_id and not self.payment_token_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always'):

                token_id = self.env['payment.token'].create({
                    'card_number': data.get('card_number'),
                    'holder_name': data.get('holder_name'),
                    'acquirer_id': self.acquirer_id.id,
                    'reference': data.get('reference'),
                    'partner_id':  self.partner_id.id,
                })
                self.payment_token_id = token_id
                self.write(res)
            return self
        elif status in ['failed','cancelled', 'refunded']:
            error = 'Received unrecognized status for Openpay payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='error', state_message=error)
            return self.write(res)
