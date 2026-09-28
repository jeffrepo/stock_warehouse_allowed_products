{
    "name": "Productos permitidos por almacén",
    "summary": "Restringe los productos que pueden ingresar a cada almacén",
    "description": """
Configura productos y categorías permitidas por almacén. Se permite un producto
si está seleccionado directamente o pertenece a una categoría permitida,
incluidas sus subcategorías. Ambas listas vacías permiten todos los productos.
Bloquea el ingreso de otros productos a las ubicaciones internas y de tránsito,
incluidas sububicaciones. Valida movimientos, operaciones y aumentos de stock.
""",
    "version": "15.0.1.1.0",
    "category": "Inventory/Inventory",
    "author": "Quemen",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": ["views/stock_warehouse_views.xml"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
