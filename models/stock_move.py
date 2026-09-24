from odoo import models
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        # Check before reserving or creating downstream operations. Negative
        # demands are reversed by Odoo; check their effective destination.
        for move in self.filtered(lambda move: move.state == "draft"):
            comparison = float_compare(
                move.product_uom_qty, 0,
                precision_rounding=move.product_uom.rounding,
            )
            if comparison:
                destination = (
                    move.location_dest_id if comparison > 0 else move.location_id
                )
                destination._check_warehouse_allowed_product(move.product_id)
        return super()._action_confirm(merge=merge, merge_into=merge_into)
