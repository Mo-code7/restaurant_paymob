# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import api, fields, models


class RestaurantDashboard(models.TransientModel):
    _name = 'restaurant.dashboard'
    _description = 'Restaurant Dashboard'

    # ─── Today's statistics ────────────────────────────────────────────
    today_orders        = fields.Integer(string='Today Ordes',  compute='_compute_stats')
    today_revenue       = fields.Monetary(string='Today Revenue', compute='_compute_stats')
    today_paid          = fields.Integer(string='Today Paid',  compute='_compute_stats')
    today_pending       = fields.Integer(string='Today Pending', compute='_compute_stats')

    # ─── Week's statistics ──────────────────────────────────────────
    week_orders         = fields.Integer(string='Week Orders',   compute='_compute_stats')
    week_revenue        = fields.Monetary(string='Week Revenue', compute='_compute_stats')

    # ─── Most requested items ────────────────────────────────────────
    top_product_name    = fields.Char(string='Top Products', compute='_compute_stats')
    top_product_qty     = fields.Float(string='Quantity',    compute='_compute_stats')

    currency_id         = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )

    @api.depends()
    def _compute_stats(self):
        today     = date.today()
        week_start = today - timedelta(days=today.weekday())

        Order = self.env['restaurant.order']
        Line  = self.env['restaurant.order.line']

        for rec in self:
            # Today
            today_recs = Order.search([
                ('create_date', '>=', f'{today} 00:00:00'),
                ('state', 'not in', ['cancel', 'draft']),
            ])
            rec.today_orders  = len(today_recs)
            rec.today_revenue = sum(today_recs.mapped('amount_total'))
            rec.today_paid    = len(today_recs.filtered(
                lambda o: o.payment_status == 'success'))
            rec.today_pending = len(today_recs.filtered(
                lambda o: o.payment_status == 'pending'))

            # Week
            week_recs = Order.search([
                ('create_date', '>=', f'{week_start} 00:00:00'),
                ('state', 'not in', ['cancel', 'draft']),
            ])
            rec.week_orders  = len(week_recs)
            rec.week_revenue = sum(week_recs.mapped('amount_total'))

            # Most requested items (This week)
            if week_recs:
                self.env.cr.execute("""
                    SELECT p.name->>'ar_001' AS pname,
                           COALESCE(p.name->>'ar_001', p.name->>'en_US') AS pname_fallback,
                           SUM(rol.product_qty) AS total_qty
                    FROM restaurant_order_line rol
                    JOIN product_product pp ON pp.id = rol.product_id
                    JOIN product_template p  ON p.id = pp.product_tmpl_id
                    WHERE rol.order_id = ANY(%s)
                    GROUP BY p.name
                    ORDER BY total_qty DESC
                    LIMIT 1
                """, [week_recs.ids])
                row = self.env.cr.fetchone()
                if row:
                    rec.top_product_name = row[0] or row[1] or 'Undefined'
                    rec.top_product_qty  = row[2]
                else:
                    rec.top_product_name = 'No data available'
                    rec.top_product_qty  = 0
            else:
                rec.top_product_name = 'No data available'
                rec.top_product_qty  = 0

    def action_open_orders(self):
        return {
            'type':      'ir.actions.act_window',
            'name':      'Restaurant Orders',
            'res_model': 'restaurant.order',
            'view_mode': 'list,kanban,form',
        }

    def action_open_report(self):
        return {
            'type':      'ir.actions.act_window',
            'name':      'Sales Report',
            'res_model': 'restaurant.sale.report',
            'view_mode': 'pivot,graph,list',
        }
