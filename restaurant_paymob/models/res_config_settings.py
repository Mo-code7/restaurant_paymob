# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    paymob_api_key = fields.Char(
        string='PayMob API Key',
        config_parameter='restaurant_paymob.api_key',
    )
    paymob_integration_id = fields.Char(
        string='PayMob Integration ID',
        config_parameter='restaurant_paymob.integration_id',
    )
    paymob_iframe_id = fields.Char(
        string='PayMob iFrame ID',
        config_parameter='restaurant_paymob.iframe_id',
    )
    paymob_hmac_secret = fields.Char(
        string='PayMob HMAC Secret (للـ Webhook)',
        config_parameter='restaurant_paymob.hmac_secret',
    )
