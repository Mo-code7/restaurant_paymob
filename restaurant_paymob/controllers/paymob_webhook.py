# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymobWebhookController(http.Controller):
    """
    Webhook لاستقبال تأكيد الدفع من PayMob تلقائياً.
    
    URL: https://yourdomain.com/paymob/webhook
    اضبط هذا الـ URL في لوحة تحكم PayMob تحت:
    Settings > Integrations > Transaction Processed Callback
    """

    @http.route(
        '/paymob/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def paymob_webhook(self, **kwargs):
        try:
            raw_data = request.httprequest.data
            data     = json.loads(raw_data)
            _logger.info("PayMob Webhook received: %s", json.dumps(data, indent=2))

            # ─── Validation HMAC (Security) ───────────────────────────
            hmac_secret = request.env['ir.config_parameter'].sudo().get_param(
                'restaurant_paymob.hmac_secret'
            )
            if hmac_secret:
                received_hmac = request.httprequest.args.get('hmac', '')
                if not self._verify_hmac(data, hmac_secret, received_hmac):
                    _logger.warning("PayMob Webhook: HMAC verification failed!")
                    return request.make_response('Unauthorized', status=401)

            # ─── Data processing ─────────────────────────────────
            obj         = data.get('obj', {})
            success     = obj.get('success', False)
            pending     = obj.get('pending', False)
            merchant_order_id = (
                obj.get('order', {})
                   .get('merchant_order_id', '')
            )
            transaction_id = str(obj.get('id', ''))

            if not merchant_order_id:
                _logger.warning("PayMob Webhook: merchant_order_id not available")
                return request.make_response('OK', status=200)

            # ─── Order update ─────────────────────────────────────
            order = request.env['restaurant.order'].sudo().search(
                [('name', '=', merchant_order_id)], limit=1
            )
            if not order:
                _logger.warning(
                    "PayMob Webhook: Order '%s' not available in Odoo",
                    merchant_order_id
                )
                return request.make_response('OK', status=200)

            if success and not pending:
                order.write({
                    'state':                'paid',
                    'payment_status':       'success',
                    'paymob_transaction_id': transaction_id,
                })
                order.message_post(
                    body=_(
                        'Payment was successfully made via PayMob✅\n'
                        'Transaction ID: %s'
                    ) % transaction_id
                )
                _logger.info(
                    "PayMob: Order %s paid successfully. Transaction: %s",
                    merchant_order_id, transaction_id
                )

            elif not success and not pending:
                order.write({'payment_status': 'failed'})
                order.message_post(
                    body=_('PayMob payment failed❌. Transaction ID: %s') % transaction_id
                )
                _logger.warning(
                    "PayMob: Payment failed for order %s", merchant_order_id
                )

            return request.make_response('OK', status=200)

        except json.JSONDecodeError:
            _logger.error("PayMob Webhook: Invalid JSON")
            return request.make_response('Bad Request', status=400)
        except Exception as e:
            _logger.exception("PayMob Webhook Error: %s", str(e))
            return request.make_response('Internal Server Error', status=500)

    def _verify_hmac(self, data, secret, received_hmac):
        """
        التحقق من صحة الـ HMAC القادم من PayMob.
        PayMob بيبعت HMAC كـ query parameter في الـ URL.
        """
        obj = data.get('obj', {})

        # The fields that PayMob calculates HMAC on (in order)
        hmac_fields = [
            'amount_cents', 'created_at', 'currency', 'error_occured',
            'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure',
            'is_auth', 'is_capture', 'is_refunded', 'is_standalone_payment',
            'is_voided', 'order.id', 'owner', 'pending',
            'source_data.pan', 'source_data.sub_type', 'source_data.type',
            'success',
        ]

        values = []
        for field in hmac_fields:
            if '.' in field:
                keys  = field.split('.')
                value = obj
                for k in keys:
                    value = value.get(k, '') if isinstance(value, dict) else ''
            else:
                value = obj.get(field, '')
            values.append(str(value))

        concatenated = ''.join(values)
        computed_hmac = hmac.new(
            secret.encode('utf-8'),
            concatenated.encode('utf-8'),
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(computed_hmac, received_hmac)
