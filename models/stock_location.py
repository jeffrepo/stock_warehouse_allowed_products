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
            allowed_categories = warehouse.allowed_category_ids
            if not (allowed_products or allowed_categories):
                continue
            if product.id in allowed_products.ids:
                continue
            if allowed_categories:
                # parent_path includes the category itself and all ancestors.
                # Read it with the same policy permissions as the warehouse.
                category_path = product.sudo().categ_id.parent_path or ""
                category_ids = {int(value) for value in category_path.split("/") if value}
                if category_ids.intersection(allowed_categories.ids):
                    continue
            raise ValidationError(_(
                "El producto '%(product)s' no está permitido en el almacén "
                "'%(warehouse)s' (ubicación destino: %(location)s). "
                "Agrégalo a los productos permitidos, selecciona su categoría "
                "en las categorías permitidas del almacén o cambia la "
                "ubicación destino."
            ) % {
                "product": product.display_name,
                "warehouse": warehouse.display_name,
                "location": location.display_name,
            })
