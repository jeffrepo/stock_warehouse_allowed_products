from odoo import models
from odoo.tools.float_utils import float_compare


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _action_done(self):
        # Detailed operations and putaway rules can override the move's
        # destination. Recheck the current policy immediately before moving stock.
        for line in self:
            if float_compare(
                line.qty_done, 0,
                precision_rounding=line.product_uom_id.rounding,
            ) > 0:
                line.location_dest_id._check_warehouse_allowed_product(line.product_id)
        return super()._action_done()
