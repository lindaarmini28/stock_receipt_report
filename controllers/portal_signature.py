# -*- coding: utf-8 -*-
import base64
import json
from odoo import http, fields
from odoo.http import request


class PortalSignatureController(http.Controller):
    """Controller for vendor signature via public portal link."""

    def _format_date(self, dt):
        """Format datetime to date only (no time)."""
        if not dt:
            return ''
        try:
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return ''

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
            # Format vendor_signed_date (date only)
            signed_date_str = self._format_date(picking.vendor_signed_date)
            return request.render('stock_receipt_report.receipt_sign_already_signed', {
                'picking': picking,
                'vendor_signed_date_str': signed_date_str,
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

    @http.route('/receipt/sign/<token>/report', type='http', auth='public', website=False)
    def receipt_report_pdf(self, token, **kwargs):
        """Public route to view receipt PDF using token (no login required)."""
        picking = request.env['stock.picking'].sudo().search([
            ('vendor_sign_token', '=', token)
        ], limit=1)
        
        if not picking:
            return request.not_found()
        
        # Generate PDF report
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'stock_receipt_report.action_report_receipt',
            [picking.id]
        )
        
        # Return PDF response
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="Receipt-{picking.name}.pdf"'),
        ]
        return request.make_response(pdf_content, headers=headers)
