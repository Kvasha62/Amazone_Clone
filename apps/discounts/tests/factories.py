from decimal import Decimal
from django.utils import timezone
from apps.discounts.models import Coupon, Campaign


def create_test_campaign(**kwargs):
    now = timezone.now()
    defaults = {
        'name': kwargs.pop('name', 'Test Campaign'),
        'is_active': True,
        'started_at': now,
        'ended_at': now + timezone.timedelta(days=30),
    }
    defaults.update(kwargs)
    return Campaign.objects.create(**defaults)


def create_test_coupon(**kwargs):
    now = timezone.now()
    defaults = {
        'code': kwargs.pop('code', 'TEST10'),
        'discount_type': kwargs.pop('discount_type', 'percent'),
        'discount_value': kwargs.pop('discount_value', Decimal('10.00')),
        'min_order_amount': Decimal('0.00'),
        'max_total_uses': 100,
        'max_uses_per_user': 1,
        'started_at': now,
        'ended_at': now + timezone.timedelta(days=30),
        'is_active': True,
    }
    defaults.update(kwargs)
    return Coupon.objects.create(**defaults)
