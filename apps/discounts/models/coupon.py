# ────────────────────────────────────────────────────────────────────────
# apps/discounts/models/coupon.py — купон (промокод).
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Уникальный код (SUMMER2025, BLACKFRI50)
#   • Тип скидки: процент или фиксированная сумма
#   • Значение скидки (50 = 50% или 500₽)
#   • Минимальная сумма заказа для применения
#   • Лимит использований (total + per-user)
#   • Срок действия (started_at / ended_at)
#   • Опциональная привязка к Campaign
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.discounts.constants import (
    DISCOUNT_TYPE_CHOICES,
    DISCOUNT_TYPE_PERCENT,
    MAX_COUPON_CODE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_TIMES_USED,
)
from apps.discounts.managers.coupon_manager import CouponManager


class Coupon(BaseModel):
    """Купон / промокод.

    Coupon owns its usage accounting. Active applications are recorded by
    ``CouponUsage`` and the denormalized ``times_used`` counter is maintained
    only through ``DiscountService.register_usage/release_usage``.
    """

    objects = CouponManager()

    code = models.CharField(
        verbose_name='Код купона',
        max_length=MAX_COUPON_CODE_LENGTH,
        unique=True,
        db_index=True,
        help_text='Уникальный код: SUMMER2025, BLACKFRI50 и т.д.',
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        default='',
        max_length=MAX_DESCRIPTION_LENGTH,
    )
    discount_type = models.CharField(
        verbose_name='Тип скидки',
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_TYPE_PERCENT,
    )
    discount_value = models.DecimalField(
        verbose_name='Значение скидки',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Процент (1-100) или фиксированная сумма в рублях.',
    )
    max_discount = models.DecimalField(
        verbose_name='Макс. скидка (₽)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Только для процентной скидки. Ограничивает сверху.',
    )
    min_order_amount = models.DecimalField(
        verbose_name='Мин. сумма заказа',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Заказ должен быть ≥ этой суммы для применения купона.',
    )
    max_total_uses = models.PositiveIntegerField(
        verbose_name='Макс. использований (всего)',
        default=MAX_TIMES_USED,
        help_text='0 = не ограничено.',
    )
    max_uses_per_user = models.PositiveIntegerField(
        verbose_name='Макс. использований (на пользователя)',
        default=1,
        help_text='Сколько раз один пользователь может применить купон.',
    )
    times_used = models.PositiveIntegerField(
        verbose_name='Использован (раз)',
        default=0,
    )
    started_at = models.DateTimeField(
        verbose_name='Действует с',
        db_index=True,
    )
    ended_at = models.DateTimeField(
        verbose_name='Действует до',
        db_index=True,
    )
    campaign = models.ForeignKey(
        'discounts.Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coupons',
        verbose_name='Кампания',
    )
    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Купон'
        verbose_name_plural = 'Купоны'
        ordering = ('-created_at',)
        indexes = [
            models.Index(
                fields=['code', 'is_active'],
                name='coupon_code_active_idx',
            ),
        ]

    def __str__(self):
        return f'{self.code} ({self.get_discount_type_display()} {self.discount_value})'

    @property
    def is_valid_now(self) -> bool:
        """True if the coupon is active and within its validity window."""
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.started_at <= now <= self.ended_at

    @property
    def is_exhausted(self) -> bool:
        """True if the global usage limit is exhausted."""
        if self.max_total_uses == 0:
            return False
        return self.times_used >= self.max_total_uses

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        """Calculate the discount amount without changing persistent state."""
        if self.discount_type == DISCOUNT_TYPE_PERCENT:
            discount = order_amount * (self.discount_value / Decimal('100'))
            if self.max_discount is not None:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value

        discount = min(discount, order_amount)
        return discount.quantize(Decimal('0.01'))
