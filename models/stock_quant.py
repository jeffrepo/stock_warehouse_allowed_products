from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _update_available_quantity(
        self, product_id, location_id, quantity, lot_id=None, package_id=None,
        owner_id=None, in_date=None,
    ):
        # Also cover corrections to completed operations and stock increases
        # made by other modules. Decreases remain possible for existing stock.
        if quantity > 0:
            location_id._check_warehouse_allowed_product(product_id)
        return super()._update_available_quantity(
            product_id, location_id, quantity, lot_id=lot_id,
            package_id=package_id, owner_id=owner_id, in_date=in_date,
        )
