from decimal import Decimal
from django.test import TestCase
from apps.discounts.tests.factories import create_test_coupon, create_test_campaign
from apps.discounts.models import Coupon


class CouponModelTests(TestCase):

    def test_create_coupon(self):
        c = create_test_coupon()
        self.assertIsNotNone(c.pk)
        self.assertEqual(c.code, 'TEST10')
        self.assertTrue(c.is_active)

    def test_unique_code(self):
        create_test_coupon(code='UNIQUE')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            create_test_coupon(code='UNIQUE')

    def test_str(self):
        c = create_test_coupon(discount_type='percent', discount_value=Decimal('25'))
        self.assertIn('TEST10', str(c))

    def test_is_valid_now(self):
        c = create_test_coupon()
        self.assertTrue(c.is_valid_now)

    def test_is_valid_now_inactive(self):
        c = create_test_coupon(is_active=False)
        self.assertFalse(c.is_valid_now)

    def test_is_exhausted(self):
        c = create_test_coupon(max_total_uses=2, times_used=2)
        self.assertTrue(c.is_exhausted)

    def test_is_not_exhausted_unlimited(self):
        c = create_test_coupon(max_total_uses=0, times_used=1000)
        self.assertFalse(c.is_exhausted)

    def test_calculate_discount_percent(self):
        c = create_test_coupon(
            discount_type='percent', discount_value=Decimal('10'),
        )
        self.assertEqual(c.calculate_discount(Decimal('1000')), Decimal('100.00'))

    def test_calculate_discount_percent_with_max(self):
        c = create_test_coupon(
            discount_type='percent', discount_value=Decimal('50'),
            max_discount=Decimal('200'),
        )
        # 50% от 1000 = 500, но max = 200
        self.assertEqual(c.calculate_discount(Decimal('1000')), Decimal('200.00'))

    def test_calculate_discount_fixed(self):
        c = create_test_coupon(
            discount_type='fixed', discount_value=Decimal('500'),
        )
        self.assertEqual(c.calculate_discount(Decimal('1000')), Decimal('500.00'))

    def test_calculate_discount_fixed_exceeds_amount(self):
        c = create_test_coupon(
            discount_type='fixed', discount_value=Decimal('5000'),
        )
        # Скидка 5000, заказ 1000 → скидка = 1000
        self.assertEqual(c.calculate_discount(Decimal('1000')), Decimal('1000.00'))


class CampaignModelTests(TestCase):

    def test_create_campaign(self):
        camp = create_test_campaign()
        self.assertIsNotNone(camp.pk)
        self.assertTrue(camp.is_running)

    def test_campaign_inactive(self):
        camp = create_test_campaign(is_active=False)
        self.assertFalse(camp.is_running)
