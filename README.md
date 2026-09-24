# Productos permitidos por almacén

Módulo técnico: `stock_warehouse_allowed_products`

Versión: Odoo 15.0 · Dependencia: `stock` · Licencia: LGPL-3

## Configuración

1. Instalar el módulo desde Aplicaciones.
2. Abrir **Inventario → Configuración → Almacenes** y seleccionar un almacén.
3. En **Control de productos → Productos permitidos**, agregar los productos que
   puede recibir. La selección se realiza por variante (`product.product`).

**Una lista vacía permite todos los productos.** Una lista con productos activa
la restricción. Vaciarla nuevamente elimina la restricción del almacén.

Por ejemplo, si el almacén B permite los productos 1 y 2, un traslado del producto
3 desde cualquier origen a B se bloquea con un mensaje que identifica el
producto, el almacén y la ubicación destino.

## Alcance

- Incluye todas las ubicaciones internas y de tránsito descendientes de la
  ubicación vista del almacén: existencias, entrada, calidad y sububicaciones.
- Se determina el almacén por la ubicación destino real, independientemente del
  almacén del tipo de operación o de la ubicación origen.
- Se comprueba al confirmar movimientos y nuevamente al ejecutar sus operaciones
  detalladas, incluso si la configuración cambió después de confirmar.
- Cubre traslados internos, recepciones, devoluciones, productos terminados de
  fabricación y ajustes positivos de inventario mediante el flujo normal de Odoo.
- También protege aumentos de existencias y correcciones de operaciones hechas
  que pasan por `_update_available_quantity`.
- Un movimiento con productos no permitidos genera un error y la transacción se
  revierte; no se omiten productos silenciosamente.
- Conserva los permisos estándar de Odoo para editar almacenes. Solo se usa
  `sudo()` para leer la política de destino, nunca para ejecutar el movimiento.
- Los productos deben pertenecer a la misma compañía del almacén o ser compartidos.

La configuración no elimina ni modifica existencias previas. Si ya hay productos
no permitidos, se pueden retirar hacia ubicaciones permitidas o reducir mediante
un ajuste; no se podrán volver a ingresar ni trasladar a otra ubicación del mismo
almacén restringido. Las ubicaciones virtuales de cliente, proveedor, producción
e inventario, y las ubicaciones sin almacén, no tienen esta restricción.

La regla protege las operaciones de inventario de Odoo; no intercepta SQL directo
ni escrituras personalizadas directas sobre `stock.quant.quantity` que omitan sus
métodos de inventario. No modifica rutas ni anticipa destinos de futuros traslados
que aún no existan: cada movimiento se comprueba contra su propio destino.

## Instalación

Colocar la carpeta `stock_warehouse_allowed_products` en una ruta de addons,
reiniciar Odoo, actualizar la lista de aplicaciones e instalar
**Productos permitidos por almacén**. No requiere depender del módulo `quemen`.

## Pruebas

La suite usa movimientos, operaciones detalladas y existencias reales del ORM.
Ejecutarla en una base de pruebas de Odoo 15, con la carpeta que contiene este
módulo incluida en `--addons-path`:

```sh
odoo-bin -d test_warehouse_allowed_products \
  -i stock_warehouse_allowed_products \
  --test-enable --test-tags /stock_warehouse_allowed_products \
  --stop-after-init --without-demo=all
```

Las pruebas cubren listas vacías, destinos anidados, recepciones desde distintos
orígenes, cambios de configuración, destinos de operaciones detalladas,
operaciones mixtas, ajustes de inventario, correcciones posteriores, salidas de
existencias previas, productos archivados y separación por compañía.
