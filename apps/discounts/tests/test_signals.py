from django.test import TestCase
from apps.discounts.tests.factories import create_test_coupon


class DiscountSignalTests(TestCase):

    def test_signal_on_create(self):
        coupon = create_test_coupon(code='SIG')
        self.assertIsNotNone(coupon.pk)
