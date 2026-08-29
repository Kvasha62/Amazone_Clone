from django.conf import settings
from django.db import models

from apps.core.models.base_model import BaseModel


class CouponUsage(BaseModel):
    """Active application of a coupon to an order."""

    coupon = models.ForeignKey(
        "discounts.Coupon",
        on_delete=models.PROTECT,
        related_name="usages",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="coupon_usages",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coupon_usages",
    )

    class Meta:
        verbose_name = "Использование купона"
        verbose_name_plural = "Использования купонов"
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                name="uq_coupon_usage_order",
            ),
        ]
        indexes = [
            models.Index(
                fields=["coupon", "user"],
                name="idx_coupon_usage_coupon_user",
            ),
            models.Index(
                fields=["order"],
                name="idx_coupon_usage_order",
            ),
        ]
