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
        help="Si la lista está vacía, el almacén permite todos los productos. "
        "Si contiene productos, solo estos pueden ingresar a sus ubicaciones "
        "internas y de tránsito, incluidas todas sus sububicaciones. "
        "La selección se realiza por variante de producto.",
    )
