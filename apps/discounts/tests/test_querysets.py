from django.test import TestCase
from apps.discounts.models import Coupon
from apps.discounts.tests.factories import create_test_coupon, create_test_campaign
from django.utils import timezone
from decimal import Decimal


class CouponQuerySetTests(TestCase):

    def setUp(self):
        self.coupon_active = create_test_coupon(code='ACTIVE')
        self.coupon_expired = create_test_coupon(
            code='EXPIRED',
            ended_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.coupon_inactive = create_test_coupon(code='INACTIVE', is_active=False)

    def test_active(self):
        qs = Coupon.objects.active()
        self.assertEqual(qs.count(), 2)  # active + expired (both is_active=True)

    def test_valid_now(self):
        qs = Coupon.objects.valid_now()
        self.assertEqual(qs.count(), 1)
        self.assertIn(self.coupon_active, qs)

    def test_not_exhausted(self):
        c = create_test_coupon(code='EXHAUST', max_total_uses=1, times_used=1)
        qs = Coupon.objects.not_exhausted()
        self.assertNotIn(c, qs)

    def test_for_campaign(self):
        camp = create_test_campaign()
        c = create_test_coupon(code='CAMP1', campaign=camp)
        qs = Coupon.objects.for_campaign(camp)
        self.assertIn(c, qs)

    def test_percent_type(self):
        qs = Coupon.objects.percent_type()
        self.assertEqual(qs.count(), 3)  # все 3 в setUp — percent

    def test_fixed_type(self):
        create_test_coupon(code='FIXED1', discount_type='fixed', discount_value=Decimal('100'))
        qs = Coupon.objects.fixed_type()
        self.assertEqual(qs.count(), 1)
