# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RestaurantOrderLine(models.Model):
    _name = 'restaurant.order.line'
    _description = 'Restaurant order category'

    order_id = fields.Many2one(
        'restaurant.order', string='Orders',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Category',
        required=True, domain=[('sale_ok', '=', True)],
    )
    product_qty = fields.Float(
        string='Quantity', default=1.0, required=True,
    )
    price_unit = fields.Float(
        string='Price', digits='Product Price',
    )
    tax_ids = fields.Many2many(
        'account.tax', string='Taxs',
    )
    price_subtotal = fields.Float(
        string='Total before tax',
        compute='_compute_price', store=True,
    )
    price_tax = fields.Float(
        string='Tax',
        compute='_compute_price', store=True,
    )
    notes = fields.Char(string='Notes')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
            self.tax_ids    = self.product_id.taxes_id

    @api.depends('product_qty', 'price_unit', 'tax_ids')
    def _compute_price(self):
        for line in self:
            subtotal = line.product_qty * line.price_unit
            taxes    = line.tax_ids.compute_all(
                line.price_unit,
                quantity=line.product_qty,
                currency=line.order_id.currency_id,
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_tax      = taxes['total_included'] - taxes['total_excluded']