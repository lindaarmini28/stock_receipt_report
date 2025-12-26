# -*- coding: utf-8 -*-
import base64
import json
from odoo import http, fields
from odoo.http import request


class PortalSignatureController(http.Controller):
    """Controller for vendor signature via public portal link."""

    @http.route('/receipt/test', type='http', auth='public', website=False)
    def receipt_test(self, **kwargs):
        """Simple test route to verify controller is loaded."""
        return "Controller OK!"

    @http.route('/receipt/sign/<token>', type='http', auth='public', website=False)
    def receipt_sign_page(self, token, **kwargs):
        """Display the signature page for vendor."""
        picking = request.env['stock.picking'].sudo().search([
            ('vendor_sign_token', '=', token)
        ], limit=1)
        
        if not picking:
            return request.render('stock_receipt_report.receipt_sign_not_found')
        
        if picking.vendor_signature:
            return request.render('stock_receipt_report.receipt_sign_already_signed', {
                'picking': picking,
            })
        
        return request.render('stock_receipt_report.receipt_sign_page', {
            'picking': picking,
        })

    @http.route('/receipt/sign/<token>/submit', type='json', auth='public', csrf=False)
    def receipt_sign_submit(self, token, signature=None, **kwargs):
        """Handle signature submission from vendor."""
        if not signature:
            return {'success': False, 'error': 'No signature provided'}
        
        picking = request.env['stock.picking'].sudo().search([
            ('vendor_sign_token', '=', token)
        ], limit=1)
        
        if not picking:
            return {'success': False, 'error': 'Receipt not found'}
        
        if picking.vendor_signature:
            return {'success': False, 'error': 'Already signed'}
        
        try:
            # Remove data URL prefix if present
            if ',' in signature:
                signature = signature.split(',')[1]
            
            # Save signature
            picking.write({
                'vendor_signature': signature,
                'vendor_signed_date': fields.Datetime.now(),
                'receipt_sign_state': 'signed',
            })
            
            # Log in chatter
            picking.message_post(
                body="Vendor signature received via portal.",
                message_type='notification',
            )
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
