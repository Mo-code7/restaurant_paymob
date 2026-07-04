# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class RestaurantOrder(models.Model):
    _name = 'restaurant.order'
    _description = 'Restaurant Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ─── Main Fields ───────────────────────────────────────────────
    name = fields.Char(
        string='Order ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    state = fields.Selection([
        ('draft',    'Draft'),
        ('confirmed','Confirmed'),
        ('preparing','Preparing'),
        ('ready',    'Ready'),
        ('paid',     'Paid'),
        ('done',     'Done'),
        ('cancel',   'CAncel'),
    ], string='Status', default='draft', tracking=True, index=True)

    # ─── Customer Data ─────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        required=True, tracking=True,
    )
    table_number = fields.Char(string='Table NO.')
    order_type = fields.Selection([
        ('dine_in',  'Dine in'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ], string='Order Type', default='dine_in', required=True, tracking=True)

    # ─── Categories ───────────────────────────────────────────────────
    order_line_ids = fields.One2many(
        'restaurant.order.line', 'order_id',
        string='Order Categories',
    )

    # ─── Totals ───────────────────────────────────────────────────
    amount_untaxed = fields.Monetary(
        string='Total before tax',
        compute='_compute_amounts', store=True,
    )
    amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_amounts', store=True,
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts', store=True, tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ─── PayMob ────────────────────────────────────────────────────
    paymob_order_id       = fields.Char(string='PayMob Order ID', readonly=True, copy=False)
    paymob_payment_key    = fields.Char(string='PayMob Payment Key', readonly=True, copy=False)
    paymob_transaction_id = fields.Char(string='PayMob Transaction ID', readonly=True, copy=False)
    paymob_payment_url    = fields.Char(string='Payment URL', readonly=True, copy=False)
    payment_status        = fields.Selection([
        ('pending',  'Pending'),
        ('success',  'Success'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ], string='Payment status', default='pending', tracking=True)

    notes = fields.Text(string='Notes')

    # ─── Compute ───────────────────────────────────────────────────
    @api.depends('order_line_ids.price_subtotal', 'order_line_ids.price_tax')
    def _compute_amounts(self):
        for order in self:
            untaxed = sum(order.order_line_ids.mapped('price_subtotal'))
            tax     = sum(order.order_line_ids.mapped('price_tax'))
            order.amount_untaxed = untaxed
            order.amount_tax     = tax
            order.amount_total   = untaxed + tax

    # ─── ORM Overrides ─────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'restaurant.order') or _('New')
        return super().create(vals_list)

    # ─── Actions / Buttons ─────────────────────────────────────────
    def action_confirm(self):
        for order in self:
            if not order.order_line_ids:
                raise UserError(_('You must add items to the first order!'))
            order.state = 'confirmed'

    def action_start_preparing(self):
        self.write({'state': 'preparing'})

    def action_ready(self):
        self.write({'state': 'ready'})

    def action_cancel(self):
        for order in self:
            if order.state == 'paid':
                raise UserError(_('It is not possible to cancel a paid order.'))
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ─── PayMob Integration ────────────────────────────────────────
    def action_pay_with_paymob(self):
        """الخطوة الرئيسية: يبدأ عملية الدفع عبر PayMob"""
        self.ensure_one()
        if self.amount_total <= 0:
            raise UserError(_('The total amount must be greater than zero!'))

        config = self.env['ir.config_parameter'].sudo()
        api_key        = config.get_param('restaurant_paymob.api_key')
        integration_id = config.get_param('restaurant_paymob.integration_id')
        iframe_id      = config.get_param('restaurant_paymob.iframe_id')

        if not all([api_key, integration_id, iframe_id]):
            raise UserError(_(
                'Please adjust the PayMob settings in the settings first.\n'
                '(API Key, Integration ID, iFrame ID)'
            ))

        try:
            # Step1: Authentication Token
            auth_token = self._paymob_get_auth_token(api_key)

            # Step2: Order Registration
            paymob_order = self._paymob_register_order(auth_token)

            # Step3: Payment Key
            payment_key = self._paymob_get_payment_key(
                auth_token, paymob_order['id'], integration_id
            )

            # Save Data
            payment_url = (
                f"https://accept.paymob.com/api/acceptance/iframes/"
                f"{iframe_id}?payment_token={payment_key}"
            )
            self.write({
                'paymob_order_id':    str(paymob_order['id']),
                'paymob_payment_key': payment_key,
                'paymob_payment_url': payment_url,
                'state':              'confirmed',
            })

            # Open the payment link in a new tab
            return {
                'type': 'ir.actions.act_url',
                'url':  payment_url,
                'target': 'new',
            }

        except requests.exceptions.RequestException as e:
            _logger.error("PayMob API Error: %s", str(e))
            raise UserError(_('There is a problem connecting to PayMob: %s') % str(e))

    def _paymob_get_auth_token(self, api_key):
        """Step1 Authentication Token"""
        response = requests.post(
            'https://accept.paymob.com/api/auth/tokens',
            json={'api_key': api_key},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if 'token' not in data:
            raise UserError(_('PayMob: Failed to obtain Auth Token'))
        return data['token']

    def _paymob_register_order(self, auth_token):
        """Step 2 PayMob"""
        # PayMob cents (Total × 100)
        amount_cents = int(self.amount_total * 100)

        items = []
        for line in self.order_line_ids:
            items.append({
                'name':        line.product_id.name,
                'amount_cents': int(line.price_unit * 100),
                'description': line.product_id.description_sale or line.product_id.name,
                'quantity':    str(int(line.product_qty)),
            })

        response = requests.post(
            'https://accept.paymob.com/api/ecommerce/orders',
            json={
                'auth_token':     auth_token,
                'delivery_needed': False,
                'amount_cents':   amount_cents,
                'currency':       'EGP',
                'merchant_order_id': self.name,
                'items':          items,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _paymob_get_payment_key(self, auth_token, paymob_order_id, integration_id):
        """Step3 Payment Key"""
        amount_cents = int(self.amount_total * 100)

        billing_data = {
            'apartment':    'NA',
            'email':        self.partner_id.email or 'NA',
            'floor':        'NA',
            'first_name':   self.partner_id.name.split()[0] if self.partner_id.name else 'NA',
            'street':       self.partner_id.street or 'NA',
            'building':     'NA',
            'phone_number': self.partner_id.phone or self.partner_id.mobile or 'NA',
            'shipping_method': 'NA',
            'postal_code':  'NA',
            'city':         self.partner_id.city or 'NA',
            'country':      self.partner_id.country_id.code or 'EG',
            'last_name':    self.partner_id.name.split()[-1] if self.partner_id.name else 'NA',
            'state':        self.partner_id.state_id.name or 'NA',
        }

        response = requests.post(
            'https://accept.paymob.com/api/acceptance/payment_keys',
            json={
                'auth_token':     auth_token,
                'amount_cents':   amount_cents,
                'expiration':     3600,
                'order_id':       paymob_order_id,
                'billing_data':   billing_data,
                'currency':       'EGP',
                'integration_id': int(integration_id),
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if 'token' not in data:
            raise UserError(_('PayMob: Failed to obtain Payment Key'))
        return data['token']

    def action_mark_paid(self):
        """Manual payment confirmation (Fallback)"""
        self.ensure_one()
        self.write({
            'state':          'paid',
            'payment_status': 'success',
        })
        self.message_post(body=_('Payment was confirmed manually✅'))

    def action_open_payment_url(self):
        """فتح رابط الدفع"""
        self.ensure_one()
        if not self.paymob_payment_url:
            raise UserError(_('There is no payment link. Click the first "Pay with PayMob" button.'))
        return {
            'type':   'ir.actions.act_url',
            'url':    self.paymob_payment_url,
            'target': 'new',
        }
