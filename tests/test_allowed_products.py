from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestWarehouseAllowedProducts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_a, cls.warehouse_b = cls.env["stock.warehouse"].create([
            {"name": "Allowed products A", "code": "APA"},
            {"name": "Allowed products B", "code": "APB"},
        ])
        cls.product_1, cls.product_2, cls.product_3 = cls.env["product.product"].create([
            {"name": "Allowed product %s" % number, "type": "product"}
            for number in (1, 2, 3)
        ])
        cls.allowed_products = cls.product_1 | cls.product_2
        cls.warehouse_b.allowed_product_ids = cls.allowed_products
        cls.category_allowed, cls.category_other = cls.env["product.category"].create([
            {"name": "Allowed category"}, {"name": "Other category"},
        ])
        cls.category_child, cls.category_sibling = cls.env["product.category"].create([
            {"name": name, "parent_id": cls.category_allowed.id}
            for name in ("Child category", "Sibling category")
        ])
        cls.category_grandchild = cls.env["product.category"].create({
            "name": "Grandchild category", "parent_id": cls.category_child.id,
        })
        cls.source = cls.env["stock.location"].create({
            "name": "Source shelf", "usage": "internal",
            "location_id": cls.warehouse_a.lot_stock_id.id,
        })
        cls.shelf = cls.env["stock.location"].create({
            "name": "Destination shelf", "usage": "internal",
            "location_id": cls.warehouse_b.lot_stock_id.id,
        })
        cls.deep_shelf = cls.env["stock.location"].create({
            "name": "Destination bin", "usage": "internal",
            "location_id": cls.shelf.id,
        })
        # A warehouse location does not have to be below its Stock location.
        cls.input_location = cls.env["stock.location"].create({
            "name": "Receiving area", "usage": "internal",
            "location_id": cls.warehouse_b.view_location_id.id,
        })
        cls.transit = cls.env["stock.location"].create({
            "name": "Warehouse transit", "usage": "transit",
            "location_id": cls.warehouse_b.view_location_id.id,
        })
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.customer = cls.env.ref("stock.stock_location_customers")
        for product in cls.allowed_products | cls.product_3:
            cls.env["stock.quant"]._update_available_quantity(product, cls.source, 20)

    def _move(self, product=None, destination=None, source=None, quantity=1):
        product = product if product is not None else self.product_1
        return self.env["stock.move"].create({
            "name": product.display_name,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": quantity,
            "location_id": (source or self.source).id,
            "location_dest_id": (destination or self.deep_shelf).id,
        })

    def _complete(self, move):
        move._action_confirm()
        move.quantity_done = move.product_uom_qty
        move._action_done()
        self.assertEqual(move.state, "done")

    def _quantity(self, product, location):
        return self.env["stock.quant"]._get_available_quantity(
            product, location, strict=True,
        )

    def test_allowed_products_reach_nested_location(self):
        for product in self.allowed_products:
            self._complete(self._move(product=product))
            self.assertEqual(self._quantity(product, self.deep_shelf), 1)

    def test_empty_list_allows_all_products(self):
        self.warehouse_b.allowed_product_ids = False
        self._complete(self._move(product=self.product_3))
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 1)

    def test_forbidden_product_blocked_in_all_warehouse_locations(self):
        destinations = (
            self.warehouse_b.lot_stock_id | self.shelf | self.deep_shelf
            | self.input_location | self.transit
        )
        for destination in destinations:
            with self.subTest(location=destination.complete_name):
                move = self._move(product=self.product_3, destination=destination)
                with self.assertRaisesRegex(ValidationError, "Allowed product 3"), self.cr.savepoint():
                    move._action_confirm()
                self.assertEqual(move.state, "draft")
                self.assertEqual(self._quantity(self.product_3, destination), 0)

    def test_receipts_from_any_source_are_restricted(self):
        for source in (self.source, self.supplier, self.customer):
            move = self._move(product=self.product_3, source=source)
            with self.assertRaisesRegex(ValidationError, "Allowed products B"), self.cr.savepoint():
                move._action_confirm()

    def test_destination_warehouse_overrides_operation_type(self):
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.warehouse_a.int_type_id.id,
            "location_id": self.source.id,
            "location_dest_id": self.deep_shelf.id,
        })
        move = self._move(product=self.product_3)
        move.picking_id = picking
        with self.assertRaises(ValidationError), self.cr.savepoint():
            picking.action_confirm()

    def test_allowed_picking_can_be_validated(self):
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.warehouse_a.int_type_id.id,
            "location_id": self.source.id,
            "location_dest_id": self.deep_shelf.id,
        })
        move = self._move()
        move.picking_id = picking
        picking.action_confirm()
        move.quantity_done = 1
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self._quantity(self.product_1, self.deep_shelf), 1)

    def test_policy_changed_after_confirmation_is_checked_again(self):
        self.warehouse_b.allowed_product_ids = False
        move = self._move(product=self.product_3)
        move._action_confirm()
        move.quantity_done = 1
        self.warehouse_b.allowed_product_ids = self.allowed_products
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_done()
        self.assertNotEqual(move.state, "done")
        self.assertEqual(self._quantity(self.product_3, self.source), 20)
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)

    def test_detailed_destination_is_checked(self):
        move = self._move(product=self.product_3, destination=self.warehouse_a.lot_stock_id)
        move._action_confirm()
        move.quantity_done = 1
        move.move_line_ids.location_dest_id = self.deep_shelf
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_done()
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)

    def test_mixed_transfer_does_not_move_any_stock(self):
        self.warehouse_b.allowed_product_ids = False
        moves = self._move() | self._move(product=self.product_3)
        moves._action_confirm()
        for move in moves:
            move.quantity_done = 1
        self.warehouse_b.allowed_product_ids = self.allowed_products
        with self.assertRaises(ValidationError), self.cr.savepoint():
            moves._action_done()
        for product in (self.product_1, self.product_3):
            self.assertEqual(self._quantity(product, self.source), 20)
            self.assertEqual(self._quantity(product, self.deep_shelf), 0)

    def test_inventory_increase_is_blocked(self):
        quant = self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": self.product_3.id,
            "location_id": self.deep_shelf.id,
            "inventory_quantity": 3,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 0)

    def test_existing_forbidden_stock_can_leave(self):
        self.warehouse_b.allowed_product_ids = False
        self.env["stock.quant"]._update_available_quantity(self.product_3, self.deep_shelf, 5)
        self.warehouse_b.allowed_product_ids = self.allowed_products
        self._complete(self._move(
            product=self.product_3, source=self.deep_shelf, destination=self.source,
        ))
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 4)

    def test_inventory_decrease_is_allowed(self):
        self.warehouse_b.allowed_product_ids = False
        self.env["stock.quant"]._update_available_quantity(self.product_3, self.deep_shelf, 5)
        self.warehouse_b.allowed_product_ids = self.allowed_products
        quant = self.env["stock.quant"].search([
            ("product_id", "=", self.product_3.id),
            ("location_id", "=", self.deep_shelf.id),
        ])
        quant.with_context(inventory_mode=True).inventory_quantity = 2
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 2)

    def test_outgoing_to_customer_is_allowed(self):
        self.warehouse_a.allowed_product_ids = self.allowed_products
        self._complete(self._move(product=self.product_3, destination=self.customer))

    def test_internal_move_within_restricted_warehouse_is_blocked(self):
        move = self._move(product=self.product_3, source=self.shelf)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_confirm()

    def test_direct_stock_increase_is_blocked(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["stock.quant"]._update_available_quantity(self.product_3, self.deep_shelf, 1)

    def test_completed_operation_cannot_be_redirected(self):
        move = self._move(product=self.product_3, destination=self.warehouse_a.lot_stock_id)
        self._complete(move)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move.move_line_ids.location_dest_id = self.deep_shelf
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)
        self.assertEqual(self._quantity(self.product_3, self.warehouse_a.lot_stock_id), 1)

    def test_zero_done_line_is_not_a_receipt(self):
        self.warehouse_b.allowed_product_ids = False
        move = self._move(product=self.product_3)
        move._action_confirm()
        line = self.env["stock.move.line"].create({
            "move_id": move.id, "product_id": self.product_3.id,
            "product_uom_id": self.product_3.uom_id.id,
            "location_id": self.source.id,
            "location_dest_id": self.deep_shelf.id,
            "qty_done": 0,
        })
        self.warehouse_b.allowed_product_ids = self.allowed_products
        line._action_done()
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)

    def test_allowed_product_from_other_company_is_rejected(self):
        company = self.env["res.company"].create({"name": "Other allowed products company"})
        product = self.env["product.product"].create({
            "name": "Other company product", "company_id": company.id,
        })
        with self.assertRaises(UserError), self.cr.savepoint():
            self.warehouse_b.allowed_product_ids = product

    def test_archived_allowed_product_does_not_disable_restriction(self):
        self.warehouse_b.allowed_product_ids = self.product_1
        self.product_1.active = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._move(product=self.product_3)._action_confirm()

    def test_negative_demand_checks_effective_destination(self):
        move = self._move(
            product=self.product_3, source=self.deep_shelf,
            destination=self.source, quantity=-1,
        )
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_confirm()

    def test_permission_is_per_variant(self):
        attribute = self.env["product.attribute"].create({
            "name": "Allowed size",
            "value_ids": [(0, 0, {"name": "Small"}), (0, 0, {"name": "Large"})],
        })
        template = self.env["product.template"].create({
            "name": "Variant permission", "type": "product",
            "attribute_line_ids": [(0, 0, {
                "attribute_id": attribute.id,
                "value_ids": [(6, 0, attribute.value_ids.ids)],
            })],
        })
        allowed, forbidden = template.product_variant_ids
        self.warehouse_b.allowed_product_ids = allowed
        self._complete(self._move(product=allowed, source=self.supplier))
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._move(product=forbidden, source=self.supplier)._action_confirm()

    def test_inventory_user_respects_policy_and_cannot_change_it(self):
        user = new_test_user(
            self.env, login="allowed_products_stock_user", groups="stock.group_stock_user",
        )
        self._complete(self._move().with_user(user))
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._move(product=self.product_3).with_user(user)._action_confirm()
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.warehouse_b.with_user(user).allowed_product_ids = False
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_3.categ_id = self.category_allowed
        self._complete(self._move(product=self.product_3).with_user(user))
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.warehouse_b.with_user(user).allowed_category_ids = False

    def test_category_only_allows_matching_product(self):
        self.warehouse_b.allowed_product_ids = False
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_3.categ_id = self.category_allowed
        self._complete(self._move(product=self.product_3))
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 1)

    def test_category_only_blocks_other_products(self):
        self.warehouse_b.allowed_product_ids = False
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_1.categ_id = self.category_other
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._move()._action_confirm()
        self.assertEqual(self._quantity(self.product_1, self.deep_shelf), 0)

    def test_products_and_categories_are_alternative_permissions(self):
        self.warehouse_b.allowed_product_ids = self.product_1
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_1.categ_id = self.category_other
        self.product_2.categ_id = self.category_allowed
        self.product_3.categ_id = self.category_other
        # Product 1 qualifies only by explicit selection, product 2 only by category.
        for product in (self.product_1, self.product_2):
            self._complete(self._move(product=product))
            self.assertEqual(self._quantity(product, self.deep_shelf), 1)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._move(product=self.product_3)._action_confirm()
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)

    def test_categories_include_descendants_but_not_parents_or_siblings(self):
        self.warehouse_b.allowed_product_ids = False
        self.warehouse_b.allowed_category_ids = self.category_child
        self.product_1.categ_id = self.category_grandchild
        self.product_2.categ_id = self.category_allowed
        self.product_3.categ_id = self.category_sibling
        self._complete(self._move())
        for product in (self.product_2, self.product_3):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self._move(product=product)._action_confirm()
        # Selecting the root also includes products two levels below it.
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self._complete(self._move())
        self.assertEqual(self._quantity(self.product_1, self.deep_shelf), 2)

    def test_any_selected_category_can_allow_product(self):
        self.warehouse_b.allowed_product_ids = False
        self.warehouse_b.allowed_category_ids = self.category_allowed | self.category_other
        self.product_1.categ_id = self.category_allowed
        self.product_2.categ_id = self.category_other
        for product in (self.product_1, self.product_2):
            self._complete(self._move(product=product))
            self.assertEqual(self._quantity(product, self.deep_shelf), 1)

    def test_category_removed_after_confirmation_is_checked_again(self):
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_3.categ_id = self.category_allowed
        move = self._move(product=self.product_3)
        move._action_confirm()
        move.quantity_done = 1
        # The explicit list remains configured, so removing categories restricts it.
        self.warehouse_b.allowed_category_ids = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_done()
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)
        self.assertEqual(self._quantity(self.product_3, self.source), 20)

    def test_product_category_changed_after_confirmation_is_checked_again(self):
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_3.categ_id = self.category_allowed
        move = self._move(product=self.product_3)
        move._action_confirm()
        move.quantity_done = 1
        self.product_3.categ_id = self.category_other
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_done()
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)

    def test_category_reparented_after_confirmation_is_checked_again(self):
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_3.categ_id = self.category_grandchild
        move = self._move(product=self.product_3)
        move._action_confirm()
        move.quantity_done = 1
        self.category_child.parent_id = self.category_other
        with self.assertRaises(ValidationError), self.cr.savepoint():
            move._action_done()
        self.assertEqual(self._quantity(self.product_3, self.deep_shelf), 0)

    def test_inventory_respects_categories(self):
        self.warehouse_b.allowed_product_ids = False
        self.warehouse_b.allowed_category_ids = self.category_allowed
        self.product_1.categ_id = self.category_child
        self.product_3.categ_id = self.category_other
        allowed_quant, forbidden_quant = self.env["stock.quant"].with_context(
            inventory_mode=True,
        ).create([
            {
                "product_id": product.id, "location_id": self.deep_shelf.id,
                "inventory_quantity": 3,
            }
            for product in (self.product_1, self.product_3)
        ])
        allowed_quant.action_apply_inventory()
        self.assertEqual(allowed_quant.quantity, 3)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            forbidden_quant.action_apply_inventory()
        self.assertEqual(forbidden_quant.quantity, 0)
