# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class RestaurantSaleReport(models.Model):
    _name = 'restaurant.sale.report'
    _description = 'Restaurant Sales Report'
    _auto = False
    _order = 'order_date desc'

    order_date      = fields.Date(string='Date', readonly=True)
    partner_id      = fields.Many2one('res.partner', string='Customer', readonly=True)
    order_type      = fields.Selection([
        ('dine_in',  'Dine in'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ], string='Order type', readonly=True)
    product_id      = fields.Many2one('product.product', string='Categries', readonly=True)
    product_qty     = fields.Float(string='Quantity', readonly=True)
    price_subtotal  = fields.Float(string='Total', readonly=True)
    payment_status  = fields.Selection([
        ('pending',  'Pending'),
        ('success',  'Success'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ], string='Payment status', readonly=True)
    order_count     = fields.Integer(string='Order Number', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER ()            AS id,
                    ro.create_date::DATE            AS order_date,
                    ro.partner_id,
                    ro.order_type,
                    ro.payment_status,
                    rol.product_id,
                    SUM(rol.product_qty)            AS product_qty,
                    SUM(rol.price_subtotal)         AS price_subtotal,
                    COUNT(DISTINCT ro.id)           AS order_count
                FROM restaurant_order ro
                JOIN restaurant_order_line rol ON rol.order_id = ro.id
                WHERE ro.state NOT IN ('cancel', 'draft')
                GROUP BY
                    ro.create_date::DATE,
                    ro.partner_id,
                    ro.order_type,
                    ro.payment_status,
                    rol.product_id
            )
        """ % self._table)
