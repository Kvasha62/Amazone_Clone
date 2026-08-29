import inspect

from django.test import SimpleTestCase

from apps.discounts.services.discount_service import DiscountService
from apps.orders.services.order_service import OrderService


class CouponOwnershipArchitectureTests(SimpleTestCase):
    def test_discount_service_never_mutates_order_or_opens_transaction(self):
        source = inspect.getsource(DiscountService)
        forbidden = (
            'transaction.atomic',
            'Order.objects.select_for_update',
            '.discount =',
            '.total =',
            '.save(',
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)

    def test_order_service_does_not_directly_mutate_discount_tables(self):
        source = inspect.getsource(OrderService)
        forbidden = (
            'Coupon.objects.filter',
            'Coupon.objects.update',
            'CouponUsage.objects.create',
            'CouponUsage.objects.delete',
            'coupon.save(',
            'usage.delete(',
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)

    def test_coupon_mutation_contracts_are_present(self):
        self.assertTrue(hasattr(DiscountService, 'register_usage'))
        self.assertTrue(hasattr(DiscountService, 'release_usage'))
        self.assertTrue(hasattr(OrderService, 'apply_coupon'))
        self.assertTrue(hasattr(OrderService, 'remove_coupon'))
