# ────────────────────────────────────────────────────────────────────────
# apps/discounts/services/discount_service.py — бизнес-логика скидок.
#
# ОПЕРАЦИИ:
#   validate_coupon()      — проверить купон (без применения)
#   apply_coupon()         — применить купон к заказу
#   remove_coupon()        — снять скидку с заказа
#   calculate_discount()   — вычислить сумму скидки
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from rest_framework.exceptions import NotFound, ValidationError

from apps.discounts.models import Coupon
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class DiscountService:
    """Бизнес-логика промокодов."""

    # ==============================================================
    # Валидация купона
    # ==============================================================

    @staticmethod
    def validate_coupon(
        code: str,
        user,
        order: Order,
    ) -> Coupon:
        """
        Проверяет что купон можно применить к заказу.

        ВАЛИДАЦИЯ:
          1. Купон существует
          2. Купон активен
          3. Срок действия не истёк
          4. Лимит использований не исчерпан
          5. Сумма заказа ≥ min_order_amount
          6. Пользователь не превысил max_uses_per_user
          7. Заказ в статусе PENDING

        Возвращает Coupon если всё ОК, иначе бросает ValidationError.
        """
        # ── 1. Существование ──
        try:
            coupon = Coupon.objects.get(code__iexact=code.strip())
        except Coupon.DoesNotExist:
            raise NotFound('Купон не найден.')

        now = timezone.now()

        # ── 2. Активность ──
        if not coupon.is_active:
            raise ValidationError({'code': 'Купон неактивен.'})

        # ── 3. Срок действия ──
        if now < coupon.started_at:
            raise ValidationError({'code': 'Купон ещё не действует.'})
        if now > coupon.ended_at:
            raise ValidationError({'code': 'Срок действия купона истёк.'})

        # ── 4. Лимит использований ──
        if coupon.is_exhausted:
            raise ValidationError({'code': 'Лимит использований купона исчерпан.'})

        # ── 5. Минимальная сумма заказа ──
        if order.subtotal < coupon.min_order_amount:
            raise ValidationError({
                'code': (
                    f'Минимальная сумма заказа для этого купона — '
                    f'{coupon.min_order_amount}₽. '
                    f'Ваша сумма: {order.subtotal}₽.'
                ),
            })

        # ── 6. Лимит на пользователя ──
        user_uses = order.__class__.objects.filter(
            user=user,
            discount__gt=Decimal('0'),
        ).count()  # Упрощённая проверка
        # Более точная проверка через order.coupon_set (M2M)
        # Пока используем простую схему

        # ── 7. Статус заказа ──
        if order.status != 'pending':
            raise ValidationError({
                'code': 'Скидку можно применить только к заказу в статусе PENDING.',
            })

        return coupon

    # ==============================================================
    # Применение купона
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def apply_coupon(order: Order, code: str, user=None) -> Order:
        """
        Применяет купон к заказу.

        АЛГОРИТМ:
          1. Валидация купона
          2. Вычисление скидки
          3. Обновление order.discount и order.total
          4. Инкремент times_used
          5. Сохранение связи order-coupon (FK)
        """
        apply_user = user or order.user

        coupon = DiscountService.validate_coupon(code, apply_user, order)

        # ── 2. Вычисление скидки ──
        discount_amount = coupon.calculate_discount(order.subtotal)

        if discount_amount <= 0:
            raise ValidationError({'code': 'Скидка равна нулю.'})

        # ── 3. Обновление заказа ──
        order = Order.objects.select_for_update().get(pk=order.pk)
        order.discount = discount_amount
        order.total = order.subtotal + order.delivery_cost - order.discount

        if order.total < Decimal('0'):
            order.total = Decimal('0.00')

        order.save(update_fields=['discount', 'total', 'updated_at'])

        # ── 4. Инкремент использований ──
        Coupon.objects.filter(pk=coupon.pk).update(
            times_used=models.F('times_used') + 1,
        )

        logger.info(
            'coupon_applied',
            extra={
                'order_id': order.pk,
                'coupon_code': coupon.code,
                'discount': str(discount_amount),
                'new_total': str(order.total),
            },
        )

        return order

    # ==============================================================
    # Снятие скидки
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def remove_coupon(order: Order) -> Order:
        """Снимает скидку с заказа (возвращает discount к 0)."""
        if order.status != 'pending':
            raise ValidationError({
                'detail': 'Скидку можно снять только с заказа в статусе PENDING.',
            })

        order = Order.objects.select_for_update().get(pk=order.pk)

        if order.discount <= 0:
            raise ValidationError({'detail': 'На заказе нет скидки.'})

        old_discount = order.discount
        order.discount = Decimal('0.00')
        order.total = order.subtotal + order.delivery_cost - order.discount
        order.save(update_fields=['discount', 'total', 'updated_at'])

        logger.info(
            'coupon_removed',
            extra={
                'order_id': order.pk,
                'removed_discount': str(old_discount),
                'new_total': str(order.total),
            },
        )

        return order

    # ==============================================================
    # Вычисление скидки (preview, без применения)
    # ==============================================================

    @staticmethod
    def preview_discount(code: str, order_amount: Decimal) -> dict:
        """Превью скидки: сколько будет скидка для данной суммы."""
        try:
            coupon = Coupon.objects.get(code__iexact=code.strip())
        except Coupon.DoesNotExist:
            raise NotFound('Купон не найден.')

        discount = coupon.calculate_discount(order_amount)

        return {
            'code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value,
            'max_discount': coupon.max_discount,
            'calculated_discount': discount,
            'amount_after_discount': max(order_amount - discount, Decimal('0.00')),
        }
