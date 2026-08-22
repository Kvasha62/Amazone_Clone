"""
Тесты QuerySet цены.
"""
from decimal import Decimal

from django.test import TestCase

from apps.pricing.models import Price
from apps.pricing.tests.factories import PricingTestCase


class PriceQuerySetTests(PricingTestCase):

    def test_for_variant(self):
        Price.objects.create(variant=self.variant_a, price=Decimal('100.00'))
        qs = Price.objects.for_variant(self.variant_a)
        self.assertEqual(qs.count(), 1)

    def test_on_sale(self):
        Price.objects.create(variant=self.variant_a, price=Decimal('100.00'))
        Price.objects.create(
            variant=self.variant_b, price=Decimal('100.00'),
            sale_price=Decimal('80.00'),
        )
        qs = Price.objects.on_sale()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().variant, self.variant_b)

    def test_for_product(self):
        Price.objects.create(variant=self.variant_a, price=Decimal('100.00'))
        Price.objects.create(variant=self.variant_b, price=Decimal('200.00'))
        qs = Price.objects.for_product(self.product)
        self.assertEqual(qs.count(), 2)
