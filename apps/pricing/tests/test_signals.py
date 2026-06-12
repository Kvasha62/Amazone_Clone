"""
Тесты сигналов ценообразования.
"""
import weakref

from decimal import Decimal

from django.db.models.signals import post_save
from django.test import TestCase

from apps.pricing.models import Price
from apps.pricing.signals import recalculate_on_price_save
from apps.pricing.tests.factories import PricingTestCase


class PriceSignalTests(PricingTestCase):

    def test_signal_function_exists(self):
        self.assertTrue(hasattr(recalculate_on_price_save, '__name__'))

    def test_signal_connected_to_post_save(self):
        found = False
        for entry in post_save.receivers:
            for item in entry:
                if isinstance(item, weakref.ref):
                    func = item()
                elif callable(item):
                    func = item
                else:
                    continue
                if func is not None and getattr(func, '__name__', '') == 'recalculate_on_price_save':
                    found = True
                    break
            if found:
                break
        self.assertTrue(found, 'recalculate_on_price_save не подключена к post_save')

    def test_price_save_updates_product_min_max(self):
        """Сохранение цены через ORM обновляет min/max на товаре."""
        Price.objects.create(variant=self.variant_a, price=Decimal('100.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))
