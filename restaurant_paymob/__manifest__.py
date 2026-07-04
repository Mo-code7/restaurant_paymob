# -*- coding: utf-8 -*-
{
    'name': 'Restaurant PayMob Integration',
    'version': '19.0.1.0.0',
    'category': 'Restaurant',
    'summary': 'Manage restaurant orders with the PayMob payment gateway',
    'description': """
        Managing restaurant orders with the PayMob payment gateway is an integrated module for managing restaurant orders with support for electronic payment via PayMob. 
        - Managing requests and stages 
        - Electronic payment via PayMob (3 official steps) 
        - Webhook to automatically confirm payment with HMAC security 
        - Dashboard with daily and week statistics 
        - Sales reports (Pivot + Graph) 
        - Print a PDF invoice in Arabic
    """,
    'author': 'Moaz Omar',
    'website': 'https://eg.dashboard.paymob.com',
    'depends': ['base', 'mail', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/restaurant_order_views.xml',
        'views/restaurant_sale_report_views.xml',
        'views/restaurant_dashboard_views.xml',
        'views/report_restaurant_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
