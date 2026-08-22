# ────────────────────────────────────────────────────────────────────────
# apps/inventory/tests/test_services.py — тесты InventoryService.
# ────────────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from rest_framework.exceptions import ValidationError

from apps.catalog.tests.factories import CatalogTestCase
from apps.inventory.models import Stock, StockMovement
from apps.inventory.models.stock_movement import MovementKind
from apps.inventory.services.inventory_service import InventoryService
from apps.orders.tests.factories import create_test_order, create_test_user, create_test_order_item


class GetOrCreateStockTests(CatalogTestCase):
    """Тесты InventoryService.get_or_create_stock()."""

    def test_creates_stock_if_not_exists(self):
        """Если Stock нет — создаётся с quantity=0."""
        stock = InventoryService.get_or_create_stock(self.variant_128)
        self.assertEqual(stock.quantity, 0)
        self.assertEqual(stock.reserved_quantity, 0)

    def test_returns_existing_stock(self):
        """Если Stock есть — возвращается существующий."""
        Stock.objects.create(variant=self.variant_128, quantity=50)
        stock = InventoryService.get_or_create_stock(self.variant_128)
        self.assertEqual(stock.quantity, 50)


class GetAvailableQuantityTests(CatalogTestCase):
    """Тесты InventoryService.get_available_quantity()."""

    def test_returns_available(self):
        Stock.objects.create(variant=self.variant_128, quantity=100, reserved_quantity=30)
        self.assertEqual(InventoryService.get_available_quantity(self.variant_128), 70)

    def test_returns_zero_if_no_stock(self):
        self.assertEqual(InventoryService.get_available_quantity(self.variant_128), 0)


class RestockTests(CatalogTestCase):
    """Тесты InventoryService.restock()."""

    def test_restock_increases_quantity(self):
        """Пополнение увеличивает quantity."""
        Stock.objects.create(variant=self.variant_128, quantity=50)
        movement = InventoryService.restock(self.variant_128, 30)
        self.assertEqual(movement.kind, MovementKind.IN)
        self.assertEqual(movement.delta, 30)
        self.assertEqual(movement.quantity_before, 50)
        self.assertEqual(movement.quantity_after, 80)

        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.quantity, 80)

    def test_restock_creates_stock_if_not_exists(self):
        """Пополнение создаёт Stock если его нет."""
        InventoryService.restock(self.variant_128, 100)
        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.quantity, 100)

    def test_restock_zero_raises_error(self):
        """quantity=0 → ValidationError."""
        with self.assertRaises(ValidationError):
            InventoryService.restock(self.variant_128, 0)


class AdjustStockTests(CatalogTestCase):
    """Тесты InventoryService.adjust_stock()."""

    def test_adjust_increases_quantity(self):
        Stock.objects.create(variant=self.variant_128, quantity=50)
        movement = InventoryService.adjust_stock(self.variant_128, 100)
        self.assertEqual(movement.kind, MovementKind.ADJUSTMENT)
        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.quantity, 100)

    def test_adjust_decreases_quantity(self):
        Stock.objects.create(variant=self.variant_128, quantity=100)
        movement = InventoryService.adjust_stock(self.variant_128, 50)
        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.quantity, 50)

    def test_adjust_below_reserved_raises_error(self):
        """Нельзя уменьшить ниже reserved_quantity."""
        Stock.objects.create(variant=self.variant_128, quantity=100, reserved_quantity=30)
        with self.assertRaises(ValidationError):
            InventoryService.adjust_stock(self.variant_128, 20)

    def test_adjust_no_change_raises_error(self):
        """Если количество не изменилось → ValidationError."""
        Stock.objects.create(variant=self.variant_128, quantity=50)
        with self.assertRaises(ValidationError):
            InventoryService.adjust_stock(self.variant_128, 50)


class ReserveReleaseCommitTests(CatalogTestCase):
    """Тесты reserve/release/commit с заказами."""

    def setUp(self):
        # Создаём заказ с позицией, ссылающейся на variant_128.
        self.user = create_test_user()
        self.order = create_test_order(self.user)
        create_test_order_item(
            self.order,
            variant=self.variant_128,
            sku=self.variant_128.sku,
            unit_price=1000,
            quantity=5,
        )

    def test_reserve_increases_reserved(self):
        """Резервирование увеличивает reserved_quantity."""
        Stock.objects.create(variant=self.variant_128, quantity=100)
        movements = InventoryService.reserve_stock(self.order)
        self.assertEqual(len(movements), 1)
        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.reserved_quantity, 5)
        self.assertEqual(stock.quantity, 100)  # quantity не меняется

    def test_reserve_insufficient_stock_raises_error(self):
        """Недостаточно стока → ValidationError."""
        Stock.objects.create(variant=self.variant_128, quantity=3)
        with self.assertRaises(ValidationError):
            InventoryService.reserve_stock(self.order)

    def test_release_decreases_reserved(self):
        """Освобождение уменьшает reserved_quantity."""
        Stock.objects.create(variant=self.variant_128, quantity=100)
        InventoryService.reserve_stock(self.order)

        movements = InventoryService.release_stock(self.order)
        self.assertEqual(len(movements), 1)
        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.quantity, 100)  # quantity не меняется

    def test_commit_decreases_both(self):
        """Списание уменьшает И quantity, И reserved."""
        Stock.objects.create(variant=self.variant_128, quantity=100)
        InventoryService.reserve_stock(self.order)

        movements = InventoryService.commit_stock(self.order)
        self.assertEqual(len(movements), 1)
        stock = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock.quantity, 95)     # 100 - 5
        self.assertEqual(stock.reserved_quantity, 0)  # 5 - 5


class CheckAvailabilityTests(CatalogTestCase):
    """Тесты InventoryService.check_availability()."""

    def test_available(self):
        Stock.objects.create(variant=self.variant_128, quantity=100, reserved_quantity=30)
        self.assertTrue(InventoryService.check_availability(self.variant_128, 50))
        self.assertTrue(InventoryService.check_availability(self.variant_128, 70))
        self.assertFalse(InventoryService.check_availability(self.variant_128, 71))

    def test_no_stock(self):
        self.assertFalse(InventoryService.check_availability(self.variant_128, 1))
