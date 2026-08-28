from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.db import connection, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from apps.discounts.models import Coupon, CouponUsage
from apps.discounts.tests.factories import create_test_coupon
from apps.orders.services.order_service import OrderService
from apps.orders.tests.factories import create_test_order, create_test_user

User = get_user_model()


@skipUnlessDBFeature('has_select_for_update')
class CouponConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def _apply(self, order_id, user_id, code, barrier):
        connections.close_all()
        try:
            barrier.wait(timeout=10)
            user = User.objects.get(pk=user_id)
            order = __import__('apps.orders.models', fromlist=['Order']).Order.objects.get(pk=order_id)
            try:
                OrderService.apply_coupon(order, code, user=user)
                return 'ok'
            except ValidationError:
                return 'error'
        finally:
            connections.close_all()

    def _run_two(self, orders, users, code):
        from threading import Barrier

        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self._apply, order.pk, user.pk, code, barrier)
                for order, user in zip(orders, users)
            ]
            return [future.result(timeout=30) for future in futures]

    def test_last_global_slot_allows_exactly_one_apply(self):
        coupon = create_test_coupon(
            code='GLOBAL1',
            max_total_uses=1,
            max_uses_per_user=10,
        )
        user1 = create_test_user()
        user2 = create_test_user()
        order1 = create_test_order(user1, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))
        order2 = create_test_order(user2, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))

        results = self._run_two([order1, order2], [user1, user2], coupon.code)

        self.assertEqual(sorted(results), ['error', 'ok'])
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)
        self.assertEqual(CouponUsage.objects.filter(coupon=coupon).count(), 1)

    def test_per_user_limit_allows_only_one_concurrent_order(self):
        coupon = create_test_coupon(
            code='USER1',
            max_total_uses=10,
            max_uses_per_user=1,
        )
        user = create_test_user()
        order1 = create_test_order(user, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))
        order2 = create_test_order(user, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))

        results = self._run_two([order1, order2], [user, user], coupon.code)

        self.assertEqual(sorted(results), ['error', 'ok'])
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)
        self.assertEqual(
            CouponUsage.objects.filter(coupon=coupon, user=user).count(),
            1,
        )

    def test_concurrent_apply_to_same_order_is_serialized_by_order_lock(self):
        coupon = create_test_coupon(
            code='ORDER1',
            max_total_uses=10,
            max_uses_per_user=10,
        )
        user = create_test_user()
        order = create_test_order(user, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))

        results = self._run_two([order, order], [user, user], coupon.code)

        self.assertEqual(sorted(results), ['error', 'ok'])
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)
        self.assertEqual(CouponUsage.objects.filter(coupon=coupon, order=order).count(), 1)

    def test_counter_matches_usage_rows_after_concurrent_apply(self):
        coupon = create_test_coupon(
            code='COUNT1',
            max_total_uses=4,
            max_uses_per_user=2,
        )
        users = [create_test_user() for _ in range(4)]
        orders = [
            create_test_order(user, subtotal=Decimal('1000.00'), total=Decimal('1000.00'))
            for user in users
        ]

        results = self._run_two(orders[:2], users[:2], coupon.code)
        self.assertEqual(sorted(results), ['ok', 'ok'])
        results = self._run_two(orders[2:], users[2:], coupon.code)
        self.assertEqual(sorted(results), ['ok', 'ok'])

        coupon.refresh_from_db()
        self.assertEqual(
            coupon.times_used,
            CouponUsage.objects.filter(coupon=coupon).count(),
        )
