# ────────────────────────────────────────────────────────────────────────
# apps/inventory/tests/test_models.py — тесты моделей Stock и StockMovement.
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.catalog.tests.factories import CatalogTestCase
from apps.inventory.models import Stock, StockMovement
from apps.inventory.models.stock_movement import MovementKind
from apps.inventory.tests.factories import create_test_stock, create_test_movement


class StockModelTests(CatalogTestCase):
    """Тесты модели Stock."""

    def setUp(self):
        self.stock = create_test_stock(self.variant_128, quantity=100)

    def test_create_stock(self):
        """Создание остатков для варианта."""
        self.assertEqual(self.stock.quantity, 100)
        self.assertEqual(self.stock.reserved_quantity, 0)

    def test_available_quantity(self):
        """available = quantity - reserved."""
        self.assertEqual(self.stock.available_quantity, 100)
        self.stock.reserved_quantity = 30
        self.stock.save()
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.available_quantity, 70)

    def test_available_quantity_never_negative(self):
        """available_quantity не может быть < 0 (защита max(0, ...))."""
        # Этот тест проверяет property available_quantity — а не БД constraint.
        # В реальности CheckConstraint (reserved ≤ quantity) не даст
        # зарезервировать больше чем есть. Но property защищает от
        # программных ошибок — всегда возвращает max(0, ...).
        # Проверяем через property напрямую (без save):
        self.stock.quantity = 10
        self.stock.reserved_quantity = 50  # Не сохраняем — только property
        # available = max(0, 10-50) = 0
        self.assertEqual(self.stock.available_quantity, 0)

    def test_is_low_stock(self):
        """low_stock = quantity ≤ threshold."""
        self.stock.quantity = 3
        self.stock.low_stock_threshold = 5
        self.stock.save()
        self.assertTrue(self.stock.is_low_stock)

    def test_is_not_low_stock(self):
        """Не low stock когда quantity > threshold."""
        self.stock.quantity = 100
        self.stock.low_stock_threshold = 5
        self.stock.save()
        self.assertFalse(self.stock.is_low_stock)

    def test_is_out_of_stock(self):
        """out_of_stock = quantity == 0."""
        self.stock.quantity = 0
        self.stock.save()
        self.assertTrue(self.stock.is_out_of_stock)

    def test_reserved_cannot_exceed_quantity(self):
        """CheckConstraint: reserved ≤ quantity."""
        self.stock.quantity = 10
        self.stock.reserved_quantity = 20
        with self.assertRaises(IntegrityError):
            self.stock.save()

    def test_one_stock_per_variant(self):
        """OneToOne: только один Stock на вариант."""
        with self.assertRaises(IntegrityError):
            Stock.objects.create(variant=self.variant_128, quantity=50)

    def test_str_representation(self):
        """__str__ содержит SKU и количества."""
        self.stock.reserved_quantity = 30
        self.stock.save()
        s = str(self.stock)
        self.assertIn('70 avail', s)
        self.assertIn('100 total', s)


class StockMovementModelTests(CatalogTestCase):
    """Тесты модели StockMovement."""

    def setUp(self):
        self.stock = create_test_stock(self.variant_128, quantity=100)

    def test_create_movement(self):
        """Создание записи о движении."""
        mv = create_test_movement(self.stock, kind=MovementKind.IN, delta=50)
        self.assertEqual(mv.kind, MovementKind.IN)
        self.assertEqual(mv.delta, 50)

    def test_str_representation(self):
        """__str__ содержит тип и delta."""
        mv = create_test_movement(self.stock, kind=MovementKind.RESERVE, delta=30)
        s = str(mv)
        self.assertIn('Резервирование', s)
        self.assertIn('30', s)
