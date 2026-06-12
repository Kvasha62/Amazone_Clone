from decimal import Decimal
from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError
from apps.orders.tests.factories import create_test_order, create_test_user
from apps.discounts.tests.factories import create_test_coupon
from apps.discounts.services.discount_service import DiscountService
from apps.discounts.models import Coupon
from django.utils import timezone


class ValidateCouponTests(TestCase):

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(
            self.user,
            subtotal=Decimal('1000.00'),
            total=Decimal('1000.00'),
        )

    def test_validate_valid_coupon(self):
        coupon = create_test_coupon(code='VALID')
        result = DiscountService.validate_coupon('VALID', self.user, self.order)
        self.assertEqual(result.pk, coupon.pk)

    def test_validate_case_insensitive(self):
        create_test_coupon(code='Summer2025')
        result = DiscountService.validate_coupon('summer2025', self.user, self.order)
        self.assertIsNotNone(result)

    def test_validate_not_found(self):
        with self.assertRaises(NotFound):
            DiscountService.validate_coupon('NOPE', self.user, self.order)

    def test_validate_expired(self):
        create_test_coupon(
            code='OLD',
            ended_at=timezone.now() - timezone.timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            DiscountService.validate_coupon('OLD', self.user, self.order)

    def test_validate_inactive(self):
        create_test_coupon(code='OFF', is_active=False)
        with self.assertRaises(ValidationError):
            DiscountService.validate_coupon('OFF', self.user, self.order)

    def test_validate_min_order_amount(self):
        create_test_coupon(code='MIN500', min_order_amount=Decimal('5000.00'))
        with self.assertRaises(ValidationError):
            DiscountService.validate_coupon('MIN500', self.user, self.order)

    def test_validate_exhausted(self):
        create_test_coupon(code='EX', max_total_uses=1, times_used=1)
        with self.assertRaises(ValidationError):
            DiscountService.validate_coupon('EX', self.user, self.order)


class ApplyCouponTests(TestCase):

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(
            self.user,
            subtotal=Decimal('2000.00'),
            delivery_cost=Decimal('0.00'),
            total=Decimal('2000.00'),
        )

    def test_apply_percent_coupon(self):
        create_test_coupon(code='TEN', discount_type='percent', discount_value=Decimal('10'))
        order = DiscountService.apply_coupon(self.order, 'TEN')
        self.assertEqual(order.discount, Decimal('200.00'))
        self.assertEqual(order.total, Decimal('1800.00'))

    def test_apply_fixed_coupon(self):
        create_test_coupon(code='FLAT500', discount_type='fixed', discount_value=Decimal('500'))
        order = DiscountService.apply_coupon(self.order, 'FLAT500')
        self.assertEqual(order.discount, Decimal('500.00'))
        self.assertEqual(order.total, Decimal('1500.00'))

    def test_apply_increments_times_used(self):
        coupon = create_test_coupon(code='CNT', discount_value=Decimal('5'))
        DiscountService.apply_coupon(self.order, 'CNT')
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)

    def test_apply_non_pending_order(self):
        self.order.status = 'confirmed'
        self.order.save()
        create_test_coupon(code='NOP')
        with self.assertRaises(ValidationError):
            DiscountService.apply_coupon(self.order, 'NOP')


class RemoveCouponTests(TestCase):

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(
            self.user,
            subtotal=Decimal('1000.00'),
            discount=Decimal('100.00'),
            total=Decimal('900.00'),
        )

    def test_remove_coupon(self):
        order = DiscountService.remove_coupon(self.order)
        self.assertEqual(order.discount, Decimal('0.00'))
        self.assertEqual(order.total, Decimal('1000.00'))

    def test_remove_no_discount(self):
        self.order.discount = Decimal('0.00')
        self.order.total = Decimal('1000.00')
        self.order.save()
        with self.assertRaises(ValidationError):
            DiscountService.remove_coupon(self.order)


class PreviewDiscountTests(TestCase):

    def test_preview(self):
        create_test_coupon(code='PREV', discount_type='percent', discount_value=Decimal('20'))
        result = DiscountService.preview_discount('PREV', Decimal('5000'))
        self.assertEqual(result['calculated_discount'], Decimal('1000.00'))

    def test_preview_not_found(self):
        with self.assertRaises(NotFound):
            DiscountService.preview_discount('NOPE', Decimal('1000'))
