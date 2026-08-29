from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.discounts.models import Coupon, CouponUsage
from apps.orders.models import Order


class DiscountService:
    """Coupon-domain validation, calculation and usage accounting.

    This service never mutates ``orders.Order`` and never owns the outer
    transaction. Callers coordinate the transaction and order locking.
    """

    @staticmethod
    def resolve_coupon(code: str) -> Coupon:
        """Load a coupon by its public code without applying business rules."""
        try:
            return Coupon.objects.get(code__iexact=code.strip())
        except Coupon.DoesNotExist:
            raise NotFound('Купон не найден.')

    @staticmethod
    def validate_coupon(
        code: str,
        user,
        order: Order,
    ) -> Coupon:
        """Validate a coupon without mutating any domain state.

        This public compatibility method is intentionally read-only. The
        mutating apply/remove workflow lives in ``OrderService``.
        """
        coupon = DiscountService.resolve_coupon(code)
        DiscountService.validate_coupon_object(coupon, user=user, order=order)
        return coupon

    @staticmethod
    def validate_coupon_object(
        coupon: Coupon,
        *,
        user,
        order: Order,
    ) -> None:
        """Validate a coupon instance, typically after locking it."""
        now = timezone.now()

        if not coupon.is_active:
            raise ValidationError({'code': 'Купон неактивен.'})
        if now < coupon.started_at:
            raise ValidationError({'code': 'Купон ещё не действует.'})
        if now > coupon.ended_at:
            raise ValidationError({'code': 'Срок действия купона истёк.'})
        if order.subtotal < coupon.min_order_amount:
            raise ValidationError({
                'code': (
                    f'Минимальная сумма заказа для этого купона — '
                    f'{coupon.min_order_amount}₽. '
                    f'Ваша сумма: {order.subtotal}₽.'
                ),
            })
        if order.status != 'pending':
            raise ValidationError({
                'code': 'Скидку можно применить только к заказу в статусе PENDING.',
            })

    @staticmethod
    def count_user_uses(coupon: Coupon, user) -> int:
        """Count active applications for one coupon/user pair."""
        return CouponUsage.objects.filter(
            coupon_id=coupon.pk,
            user_id=user.pk,
        ).count()

    @staticmethod
    def calculate_discount(coupon: Coupon, order_amount: Decimal) -> Decimal:
        """Pure coupon calculation."""
        discount = coupon.calculate_discount(order_amount)
        if discount <= 0:
            raise ValidationError({'code': 'Скидка равна нулю.'})
        return discount

    @staticmethod
    def register_usage(
        coupon: Coupon,
        *,
        user,
        order: Order,
    ) -> CouponUsage:
        """Register one active usage and increment the coupon counter.

        The caller must already hold the authoritative Coupon row lock.
        Only discounts-owned tables are mutated here.
        """
        if CouponUsage.objects.filter(
            coupon_id=coupon.pk,
            order_id=order.pk,
        ).exists():
            raise ValidationError({'code': 'Купон уже применён к этому заказу.'})

        updated = Coupon.objects.filter(pk=coupon.pk).filter(
            models.Q(max_total_uses=0)
            | models.Q(times_used__lt=models.F('max_total_uses')),
        ).update(times_used=models.F('times_used') + 1)
        if updated != 1:
            raise ValidationError({'code': 'Лимит использований купона исчерпан.'})

        return CouponUsage.objects.create(
            coupon=coupon,
            order=order,
            user=user,
        )

    @staticmethod
    def release_usage(usage: CouponUsage) -> None:
        """Release an active usage and decrement the coupon counter.

        The caller must hold the Coupon lock before invoking this method.
        The usage row is locked last, preserving Order → Coupon → Usage.
        """
        usage = CouponUsage.objects.select_for_update().get(pk=usage.pk)

        updated = Coupon.objects.filter(
            pk=usage.coupon_id,
            times_used__gt=0,
        ).update(times_used=models.F('times_used') - 1)
        if updated != 1:
            raise ValidationError({'detail': 'Некорректный счётчик использований купона.'})

        usage.delete()

    @staticmethod
    def preview_discount(code: str, order_amount: Decimal) -> dict:
        """Preview a discount without applying it or changing usage state."""
        coupon = DiscountService.resolve_coupon(code)
        discount = coupon.calculate_discount(order_amount)

        return {
            'code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value,
            'max_discount': coupon.max_discount,
            'calculated_discount': discount,
            'amount_after_discount': max(order_amount - discount, Decimal('0.00')),
        }
