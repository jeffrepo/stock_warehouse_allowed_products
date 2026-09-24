from odoo import _, models
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = "stock.location"

    def _check_warehouse_allowed_product(self, product):
        """Check the actual destination, independently of the operation type."""
        if not product:
            return
        # Reading the policy with sudo prevents record rules from hiding it.
        # Stock operations themselves keep the caller's normal permissions.
        for location in self.sudo().with_context(active_test=False):
            if location.usage not in ("internal", "transit"):
                continue
            warehouse = location.warehouse_id
            allowed_products = warehouse.allowed_product_ids
            if allowed_products and product.id not in allowed_products.ids:
                raise ValidationError(_(
                    "El producto '%(product)s' no está permitido en el almacén "
                    "'%(warehouse)s' (ubicación destino: %(location)s). "
                    "Agrégalo a los productos permitidos del almacén o cambia "
                    "la ubicación destino."
                ) % {
                    "product": product.display_name,
                    "warehouse": warehouse.display_name,
                    "location": location.display_name,
                })
