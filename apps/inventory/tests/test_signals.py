# ────────────────────────────────────────────────────────────────────────
# apps/inventory/tests/test_signals.py — тесты сигналов склада.
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from apps.catalog.tests.factories import CatalogTestCase
from apps.inventory.tests.factories import create_test_stock


class InventorySignalTests(CatalogTestCase):
    """Тесты сигналов Stock и StockMovement."""

    def test_stock_created_signal(self):
        """post_save(created=True) — логирование создания."""
        stock = create_test_stock(self.variant_128, quantity=50)
        self.assertIsNotNone(stock.pk)

    def test_stock_updated_signal(self):
        """post_save(created=False) — логирование обновления."""
        stock = create_test_stock(self.variant_128, quantity=100)
        stock.quantity = 50
        stock.save()
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, 50)
