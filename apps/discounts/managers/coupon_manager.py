from django.db import models
from apps.discounts.querysets.coupon_queryset import CouponQuerySet


class CouponManager(models.Manager.from_queryset(CouponQuerySet)):
    pass
