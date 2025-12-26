# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    # =========================================================================
    # REFERENCE FIELDS (Computed from PO/SO via tracing)
    # These fields display reference data from origin order for Receipt/INT
    # =========================================================================

    ref_source_type = fields.Selection(
        selection=[
            ('po', 'Purchase Order'),
            ('so', 'Sales Order'),
            ('product', 'Product Default'),
        ],
        string="Reference Source",
        compute='_compute_reference_fields',
        store=False,
        help="Indicates where the reference data is coming from",
    )

    ref_product_image = fields.Binary(
        string="Product Image",
        compute='_compute_reference_fields',
        store=False,
    )

    ref_product_length = fields.Float(
        string="Length (cm)",
        compute='_compute_reference_fields',
        store=False,
        digits=(12, 1),
    )

    ref_product_width = fields.Float(
        string="Width (cm)",
        compute='_compute_reference_fields',
        store=False,
        digits=(12, 1),
    )

    ref_product_height = fields.Float(
        string="Height (cm)",
        compute='_compute_reference_fields',
        store=False,
        digits=(12, 1),
    )

    ref_qty_ordered = fields.Float(
        string="Qty Ordered",
        compute='_compute_reference_fields',
        store=False,
        help="Total quantity from the source order",
    )

    # =========================================================================
    # TRACING HELPER METHOD
    # =========================================================================

    def _get_origin_order_line(self):
        """
        Trace back via move_orig_ids to find origin purchase/sale line.
        
        Returns:
            tuple: (source_type, order_line_record) or (None, None)
            
        Logic:
        1. Check direct purchase_line_id → return ('po', line)
        2. Check direct sale_line_id → return ('so', line)
        3. Trace via move_orig_ids recursively until found
        4. Fallback: return (None, None)
        """
        self.ensure_one()

        # Priority 1: Direct link to Purchase Line
        if self.purchase_line_id:
            return ('po', self.purchase_line_id)

        # Priority 2: Direct link to Sale Line
        if self.sale_line_id:
            return ('so', self.sale_line_id)

        # Priority 3: Trace via move chain (for internal transfers)
        visited = set()
        to_check = list(self.move_orig_ids)

        while to_check:
            origin_move = to_check.pop(0)
            if origin_move.id in visited:
                continue
            visited.add(origin_move.id)

            # Check if this origin move has direct links
            if origin_move.purchase_line_id:
                return ('po', origin_move.purchase_line_id)
            if origin_move.sale_line_id:
                return ('so', origin_move.sale_line_id)

            # Continue tracing
            to_check.extend(origin_move.move_orig_ids)

        return (None, None)

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================

    @api.depends(
        'purchase_line_id',
        'sale_line_id',
        'move_orig_ids',
        'move_orig_ids.purchase_line_id',
        'move_orig_ids.sale_line_id',
        'product_id',
    )
    def _compute_reference_fields(self):
        """
        Compute reference fields by tracing to origin order line.
        
        For Receipt: directly from purchase_line_id
        For Internal Transfer: traced via move_orig_ids chain
        """
        for move in self:
            source_type, order_line = move._get_origin_order_line()
            move.ref_source_type = source_type or 'product'

            if source_type == 'po' and order_line:
                # From Purchase Order
                move.ref_product_image = getattr(order_line, 'product_image', False)
                move.ref_product_length = getattr(order_line, 'product_length', 0.0)
                move.ref_product_width = getattr(order_line, 'product_width', 0.0)
                move.ref_product_height = getattr(order_line, 'product_height', 0.0)
                move.ref_qty_ordered = order_line.product_qty

            elif source_type == 'so' and order_line:
                # From Sales Order
                move.ref_product_image = getattr(order_line, 'product_image', False)
                move.ref_product_length = getattr(order_line, 'product_length', 0.0)
                move.ref_product_width = getattr(order_line, 'product_width', 0.0)
                move.ref_product_height = getattr(order_line, 'product_height', 0.0)
                move.ref_qty_ordered = order_line.product_uom_qty

            else:
                # Fallback: Product defaults
                move.ref_product_image = move.product_id.image_128 if move.product_id else False
                move.ref_product_length = 0.0
                move.ref_product_width = 0.0
                move.ref_product_height = 0.0
                move.ref_qty_ordered = move.product_uom_qty
