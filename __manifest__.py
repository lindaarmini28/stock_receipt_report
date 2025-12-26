# -*- coding: utf-8 -*-
{
    'name': "Stock Receipt Report",
    'version': '16.0.1.2.0',
    'summary': 'Custom Receipt Report with Digital Signatures for Wabe',
    'description': """
        Custom module untuk Receipt operations di Wabe.
        
        Features:
        - Reference fields from PO/SO (product image, dimensions, qty)
        - Custom Receipt Report dengan Wabe header
        - Vendor identity, backorder tracking
        - 3-party signature section (QC, Inventory, Vendor)
        - Digital signature capture for Inventory Team on validate
        - Portal link for Vendor signature (no Odoo login required)
    """,
    'author': "CV Widhi Asih Bali Export",
    'category': 'Inventory',
    'depends': [
        'stock',
        'purchase_stock',
        'sale_stock',
        'user_signature',
        'portal',
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/receipt_sign_portal.xml',
        'report/receipt_report.xml',
        'report/receipt_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
