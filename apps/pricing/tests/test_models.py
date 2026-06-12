"""
Тесты моделей ценообразования.
"""
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.pricing.models import Price, PriceHistory
from apps.pricing.tests.factories import PricingTestCase


class PriceModelTests(PricingTestCase):

    def test_create_price(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('100.00'),
        )
        self.assertEqual(price.price, Decimal('100.00'))
        self.assertIsNone(price.sale_price)

    def test_str_no_sale(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('500.00'),
        )
        self.assertIn('500.00', str(price))

    def test_str_with_sale(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('500.00'),
            sale_price=Decimal('400.00'),
        )
        self.assertIn('400.00', str(price))

    def test_effective_price_without_sale(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('100.00'),
        )
        self.assertEqual(price.effective_price, Decimal('100.00'))

    def test_effective_price_with_sale(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('100.00'),
            sale_price=Decimal('80.00'),
        )
        self.assertEqual(price.effective_price, Decimal('80.00'))

    def test_discount_percent(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('100.00'),
            sale_price=Decimal('75.00'),
        )
        self.assertEqual(price.discount_percent, 25)

    def test_discount_percent_none_without_sale(self):
        price = Price.objects.create(
            variant=self.variant_a,
            price=Decimal('100.00'),
        )
        self.assertIsNone(price.discount_percent)

    def test_price_zero_constraint(self):
        """price=0 нарушает CheckConstraint."""
        with self.assertRaises(IntegrityError):
            Price.objects.create(
                variant=self.variant_a,
                price=Decimal('0.00'),
            )

    def test_sale_price_gt_price_constraint(self):
        """sale_price > price нарушает CheckConstraint."""
        with self.assertRaises(IntegrityError):
            Price.objects.create(
                variant=self.variant_a,
                price=Decimal('50.00'),
                sale_price=Decimal('60.00'),
            )

    def test_one_to_one_variant(self):
        """Один вариант — одна цена."""
        Price.objects.create(
            variant=self.variant_a,
            price=Decimal('100.00'),
        )
        with self.assertRaises(IntegrityError):
            Price.objects.create(
                variant=self.variant_a,
                price=Decimal('200.00'),
            )

    def test_ordering(self):
        self.assertEqual(Price._meta.ordering, ('-created_at',))


class PriceHistoryModelTests(PricingTestCase):

    def test_create_history(self):
        history = PriceHistory.objects.create(
            variant=self.variant_a,
            old_price=Decimal('100.00'),
            new_price=Decimal('90.00'),
            reason='Скидка',
        )
        self.assertEqual(history.old_price, Decimal('100.00'))
        self.assertEqual(history.new_price, Decimal('90.00'))

    def test_history_str(self):
        history = PriceHistory.objects.create(
            variant=self.variant_a,
            old_price=Decimal('100.00'),
            new_price=Decimal('90.00'),
        )
        self.assertIn('100.00', str(history))
        self.assertIn('90.00', str(history))

    def test_ordering(self):
        self.assertEqual(PriceHistory._meta.ordering, ('-created_at',))
