{
    "name": "Productos permitidos por almacén",
    "summary": "Restringe los productos que pueden ingresar a cada almacén",
    "description": """
Configura productos permitidos por almacén y bloquea el ingreso de otros
productos a sus ubicaciones internas y de tránsito, incluidas sububicaciones.
Una lista vacía permite todos los productos. Incluye validación de movimientos,
operaciones detalladas y aumentos de existencias.
""",
    "version": "15.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Quemen",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": ["views/stock_warehouse_views.xml"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
