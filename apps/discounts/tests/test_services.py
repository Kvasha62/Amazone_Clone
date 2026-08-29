from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.discounts.models import CouponUsage
from apps.discounts.services.discount_service import DiscountService
from apps.discounts.tests.factories import create_test_coupon
from apps.orders.models.order import OrderStatus
from apps.orders.services.order_service import OrderService
from apps.orders.tests.factories import create_test_order, create_test_user


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
        create_test_coupon(
            code='TEN',
            discount_type='percent',
            discount_value=Decimal('10'),
        )
        order = OrderService.apply_coupon(self.order, 'TEN', user=self.user)
        self.assertEqual(order.discount, Decimal('200.00'))
        self.assertEqual(order.total, Decimal('1800.00'))

    def test_apply_fixed_coupon(self):
        create_test_coupon(
            code='FLAT500',
            discount_type='fixed',
            discount_value=Decimal('500'),
        )
        order = OrderService.apply_coupon(self.order, 'FLAT500', user=self.user)
        self.assertEqual(order.discount, Decimal('500.00'))
        self.assertEqual(order.total, Decimal('1500.00'))

    def test_apply_creates_usage_and_increments_times_used(self):
        coupon = create_test_coupon(code='CNT', discount_value=Decimal('5'))
        OrderService.apply_coupon(self.order, 'CNT', user=self.user)
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)
        usage = CouponUsage.objects.get(coupon=coupon, order=self.order)
        self.assertEqual(usage.user_id, self.user.pk)

    def test_apply_enforces_per_user_limit(self):
        coupon = create_test_coupon(
            code='ONE',
            max_uses_per_user=1,
            max_total_uses=10,
        )
        OrderService.apply_coupon(self.order, 'ONE', user=self.user)
        second_order = create_test_order(self.user, subtotal=Decimal('2000.00'), total=Decimal('2000.00'))
        with self.assertRaises(ValidationError):
            OrderService.apply_coupon(second_order, 'ONE', user=self.user)
        self.assertEqual(CouponUsage.objects.filter(coupon=coupon, user=self.user).count(), 1)

    def test_apply_enforces_global_limit(self):
        coupon = create_test_coupon(
            code='LAST',
            max_total_uses=1,
            max_uses_per_user=10,
        )
        OrderService.apply_coupon(self.order, 'LAST', user=self.user)
        other_user = create_test_user()
        other_order = create_test_order(other_user, subtotal=Decimal('2000.00'), total=Decimal('2000.00'))
        with self.assertRaises(ValidationError):
            OrderService.apply_coupon(other_order, 'LAST', user=other_user)
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)

    def test_apply_rejects_already_discounted_order(self):
        create_test_coupon(code='NOP')
        self.order.discount = Decimal('1.00')
        self.order.save(update_fields=['discount', 'updated_at'])
        with self.assertRaises(ValidationError):
            OrderService.apply_coupon(self.order, 'NOP', user=self.user)

    def test_apply_non_pending_order(self):
        self.order.status = OrderStatus.CONFIRMED
        self.order.save(update_fields=['status', 'updated_at'])
        create_test_coupon(code='NOP')
        with self.assertRaises(ValidationError):
            OrderService.apply_coupon(self.order, 'NOP', user=self.user)


class RemoveCouponTests(TestCase):

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(
            self.user,
            subtotal=Decimal('1000.00'),
            total=Decimal('1000.00'),
        )
        create_test_coupon(
            code='REMOVE',
            discount_value=Decimal('10'),
            max_uses_per_user=2,
        )
        OrderService.apply_coupon(self.order, 'REMOVE', user=self.user)

    def test_remove_coupon_releases_usage_and_counter(self):
        coupon = self.order.coupon_usages.get().coupon
        order = OrderService.remove_coupon(self.order, user=self.user)
        coupon.refresh_from_db()
        self.assertEqual(order.discount, Decimal('0.00'))
        self.assertEqual(order.total, Decimal('1000.00'))
        self.assertEqual(coupon.times_used, 0)
        self.assertFalse(CouponUsage.objects.filter(order=order).exists())

    def test_remove_allows_reapply(self):
        OrderService.remove_coupon(self.order, user=self.user)
        order = OrderService.apply_coupon(self.order, 'REMOVE', user=self.user)
        self.assertEqual(order.discount, Decimal('100.00'))
        self.assertEqual(CouponUsage.objects.filter(order=order).count(), 1)

    def test_remove_legacy_order_without_usage_is_graceful(self):
        CouponUsage.objects.all().delete()
        self.order.discount = Decimal('100.00')
        self.order.total = Decimal('900.00')
        self.order.save(update_fields=['discount', 'total', 'updated_at'])
        order = OrderService.remove_coupon(self.order, user=self.user)
        self.assertEqual(order.discount, Decimal('0.00'))
        self.assertEqual(order.total, Decimal('1000.00'))


class CancelCouponTests(TestCase):

    def test_cancel_releases_coupon_usage(self):
        user = create_test_user()
        order = create_test_order(user, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))
        coupon = create_test_coupon(code='CANCEL', discount_value=Decimal('10'))
        OrderService.apply_coupon(order, 'CANCEL', user=user)

        order = OrderService.cancel(order, user=user)
        coupon.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.discount, Decimal('0.00'))
        self.assertEqual(order.total, Decimal('1000.00'))
        self.assertEqual(coupon.times_used, 0)
        self.assertFalse(CouponUsage.objects.filter(order=order).exists())

    # ARCH-002 (п.4): release купонного слота — ТОЛЬКО при переходе
    # PENDING → CANCELLED. Отмена уже подтверждённого/собираемого/
    # отправленного заказа НЕ освобождает слот и не трогает
    # times_used / Order.discount / Order.total.

    @staticmethod
    def _order_with_usage_in_status(status, code):
        user = create_test_user()
        order = create_test_order(
            user,
            subtotal=Decimal('1000.00'),
            total=Decimal('1000.00'),
        )
        coupon = create_test_coupon(code=code, discount_value=Decimal('10'))
        OrderService.apply_coupon(order, code, user=user)
        order.status = status
        order.save(update_fields=['status', 'updated_at'])
        return user, order, coupon

    def test_cancel_from_confirmed_keeps_coupon_usage(self):
        user, order, coupon = self._order_with_usage_in_status(
            OrderStatus.CONFIRMED, 'KEEPC',
        )
        OrderService.cancel(order, user=user)
        coupon.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(coupon.times_used, 1)
        self.assertTrue(CouponUsage.objects.filter(order=order).exists())
        self.assertEqual(order.discount, Decimal('100.00'))
        self.assertEqual(order.total, Decimal('900.00'))

    def test_cancel_from_processing_keeps_coupon_usage(self):
        user, order, coupon = self._order_with_usage_in_status(
            OrderStatus.PROCESSING, 'KEEPP',
        )
        OrderService.cancel(order, user=user)
        coupon.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(coupon.times_used, 1)
        self.assertTrue(CouponUsage.objects.filter(order=order).exists())
        self.assertEqual(order.discount, Decimal('100.00'))
        self.assertEqual(order.total, Decimal('900.00'))

    def test_cancel_from_shipped_keeps_coupon_usage(self):
        user, order, coupon = self._order_with_usage_in_status(
            OrderStatus.SHIPPED, 'KEEPS',
        )
        OrderService.cancel(order, user=user)
        coupon.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(coupon.times_used, 1)
        self.assertTrue(CouponUsage.objects.filter(order=order).exists())
        self.assertEqual(order.discount, Decimal('100.00'))
        self.assertEqual(order.total, Decimal('900.00'))


class PreviewDiscountTests(TestCase):

    def test_preview(self):
        create_test_coupon(code='PREV', discount_type='percent', discount_value=Decimal('20'))
        result = DiscountService.preview_discount('PREV', Decimal('5000'))
        self.assertEqual(result['calculated_discount'], Decimal('1000.00'))

    def test_preview_not_found(self):
        with self.assertRaises(NotFound):
            DiscountService.preview_discount('NOPE', Decimal('1000'))
