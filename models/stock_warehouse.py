from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    allowed_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="stock_warehouse_allowed_product_rel",
        column1="warehouse_id",
        column2="product_id",
        string="Productos permitidos",
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', "
        "('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Estos productos pueden ingresar aunque no pertenezcan a las "
        "categorías permitidas. La selección se realiza por variante. "
        "Si las listas de productos y categorías están vacías, se permiten "
        "todos los productos.",
    )

    allowed_category_ids = fields.Many2many(
        comodel_name="product.category",
        relation="stock_warehouse_allowed_category_rel",
        column1="warehouse_id",
        column2="category_id",
        string="Categorías permitidas",
        help="Permite todos los productos de estas categorías y sus "
        "subcategorías, además de los productos seleccionados directamente. "
        "La regla aplica a las ubicaciones internas y de tránsito del "
        "almacén, incluidas sus sububicaciones. Si ambas listas están vacías, "
        "se permiten todos los productos.",
    )
