# ────────────────────────────────────────────────────────────────────────
# apps/inventory/tests/test_querysets.py — тесты StockQuerySet.
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from apps.catalog.models import ProductVariant
from apps.catalog.tests.factories import CatalogTestCase
from apps.inventory.models import Stock
from apps.inventory.tests.factories import create_test_stock


class StockQuerySetTests(CatalogTestCase):
    """Тесты методов StockQuerySet."""

    def setUp(self):
        self.stock_full = create_test_stock(self.variant_128, quantity=100)
        self.stock_low = create_test_stock(
            self.variant_256, quantity=3, low_stock_threshold=5,
        )
        # Создаём третий вариант для пустого стока.
        self.variant_empty = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-EMPTY-STOCK',
            is_active=True,
        )
        self.stock_empty = create_test_stock(
            self.variant_empty, quantity=0,
        )

    def test_in_stock(self):
        """in_stock() — quantity > 0."""
        result = Stock.objects.in_stock()
        self.assertEqual(result.count(), 2)

    def test_out_of_stock(self):
        """out_of_stock() — quantity == 0."""
        result = Stock.objects.out_of_stock()
        self.assertEqual(result.count(), 1)

    def test_low_stock(self):
        """low_stock() — quantity ≤ threshold, quantity > 0."""
        result = Stock.objects.low_stock()
        self.assertEqual(result.count(), 1)

    def test_has_available(self):
        """has_available() — quantity > reserved."""
        self.stock_full.reserved_quantity = 30
        self.stock_full.save()
        result = Stock.objects.has_available()
        self.assertEqual(result.count(), 2)  # full + low (no reserve)

    def test_for_product(self):
        """for_product() — остатки вариантов товара."""
        result = Stock.objects.for_product(self.product)
        self.assertEqual(result.count(), 3)  # all three variants
