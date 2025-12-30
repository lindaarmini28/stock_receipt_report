# -*- coding: utf-8 -*-
import uuid
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    """Extend stock.picking for receipt report with signature capture."""
    _inherit = 'stock.picking'

    # Related field for view visibility
    picking_type_sequence_code = fields.Char(
        string="Picking Type Code",
        related='picking_type_id.sequence_code',
        store=False,
        readonly=True,
        help="Sequence code of picking type (IN, INT, PICK, PACK, OUT)",
    )

    # =============================================
    # INVENTORY TEAM SIGNATURE (auto on validate)
    # =============================================
    
    inventory_signature = fields.Binary(
        string="Inventory Signature",
        help="Signature of inventory team member who validated the receipt",
        copy=False,
    )
    inventory_signed_by_id = fields.Many2one(
        'res.users',
        string="Inventory Signed By",
        help="User who validated the receipt",
        copy=False,
    )
    inventory_signed_date = fields.Datetime(
        string="Inventory Signed Date",
        help="Date when inventory team validated the receipt",
        copy=False,
    )
    inventory_signed_date_display = fields.Char(
        string="Inventory Signed Date (Display)",
        compute='_compute_signed_dates_display',
        help="Inventory signed date formatted in company timezone",
    )

    # =============================================
    # VENDOR SIGNATURE (via portal link)
    # =============================================
    
    vendor_signature = fields.Binary(
        string="Vendor Signature",
        help="Signature from vendor via portal link",
        copy=False,
    )
    vendor_signed_date = fields.Datetime(
        string="Vendor Signed Date",
        help="Date when vendor signed the receipt",
        copy=False,
    )
    vendor_signed_date_display = fields.Char(
        string="Vendor Signed Date (Display)",
        compute='_compute_signed_dates_display',
        help="Vendor signed date formatted in company timezone",
    )
    vendor_sign_token = fields.Char(
        string="Vendor Sign Token",
        help="Unique token for vendor to access signing page",
        copy=False,
        readonly=True,
    )
    vendor_sign_url = fields.Char(
        string="Vendor Sign URL",
        compute='_compute_vendor_sign_url',
        help="Full URL for vendor to sign the receipt",
    )
    
    # =============================================
    # SIGNATURE WORKFLOW STATUS
    # =============================================
    
    receipt_sign_state = fields.Selection([
        ('draft', 'Waiting Validation'),
        ('validated', 'Validated'),
        ('requested', 'Signature Requested'),
        ('signed', 'Vendor Signed'),
    ], string="Signature Status", default='draft', copy=False, tracking=True,
       help="Tracks the receipt signature workflow status")

    def _convert_to_company_tz(self, dt):
        """Convert UTC datetime to local date (date only, no time)."""
        if not dt:
            return '____________________'
        # Simple date-only format (tanggal saja, tanpa jam)
        try:
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return '____________________'

    @api.depends('inventory_signed_date', 'vendor_signed_date', 'company_id')
    def _compute_signed_dates_display(self):
        """Compute display dates in company timezone."""
        for picking in self:
            picking.inventory_signed_date_display = picking._convert_to_company_tz(
                picking.inventory_signed_date
            )
            picking.vendor_signed_date_display = picking._convert_to_company_tz(
                picking.vendor_signed_date
            )

    @api.depends('vendor_sign_token')
    def _compute_vendor_sign_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for picking in self:
            if picking.vendor_sign_token:
                picking.vendor_sign_url = f"{base_url}/receipt/sign/{picking.vendor_sign_token}"
            else:
                picking.vendor_sign_url = False

    # =============================================
    # ACTIONS
    # =============================================
    
    def action_request_vendor_signature(self):
        """Generate token and return URL for vendor to sign."""
        self.ensure_one()
        
        # Only for Receipt operations
        if self.picking_type_id.code != 'incoming':
            raise UserError("Vendor signature request is only for Receipt operations.")
        
        # Only for validated receipts
        if self.state != 'done':
            raise UserError("Please validate the receipt first before requesting vendor signature.")
        
        # Generate token if not exists
        if not self.vendor_sign_token:
            self.vendor_sign_token = str(uuid.uuid4())
        
        # Update signature status
        self.receipt_sign_state = 'requested'
        
        # Return action to show the URL
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Signature Link',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('stock_receipt_report.view_picking_vendor_sign_url').id,
            'target': 'new',
        }

    def action_view_vendor_sign_url(self):
        """Show existing vendor sign URL in popup (for when dialog was closed)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Signature Link',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('stock_receipt_report.view_picking_vendor_sign_url').id,
            'target': 'new',
        }

    def button_validate(self):
        """Override to capture inventory signature on receipt validation."""
        for picking in self:
            # Only for Receipt operations (IN)
            if picking.picking_type_id.code == 'incoming':
                user = self.env.user
                
                # Check if user has signature
                if hasattr(user, 'signature') and user.signature:
                    picking.write({
                        'inventory_signature': user.signature,
                        'inventory_signed_by_id': user.id,
                        'inventory_signed_date': fields.Datetime.now(),
                        'receipt_sign_state': 'validated',
                    })
                else:
                    # Just record who validated without signature
                    picking.write({
                        'inventory_signed_by_id': user.id,
                        'inventory_signed_date': fields.Datetime.now(),
                        'receipt_sign_state': 'validated',
                    })
        
        return super().button_validate()
