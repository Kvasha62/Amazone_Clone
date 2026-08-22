# ────────────────────────────────────────────────────────────────────────
# apps/payments/services/payment_service.py — бизнес-логика платежей.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Service Layer»:
#   View → сериализатор (валидация) → сервис (бизнес-логика) → ORM (SQL)
#
# ОПЕРАЦИИ:
#   create_payment()     — создать платёж для заказа
#   process_payment()    — перевести в PROCESSING (отправка провайдеру)
#   confirm_payment()    — подтвердить оплату (webhook/callback)
#   fail_payment()       — отметить как FAILED
#   cancel_payment()     — отменить платёж
#   refund_payment()     — оформить возврат средств
#   handle_webhook()     — обработать вебхук от провайдера
#
# БЕЗОПАСНОСТЬ КОНКУРЕНТНОГО ДОСТУПА:
#   Все mutating-методы используют select_for_update() и transaction.atomic.
#
# 📖 https://martinfowler.com/eaaCatalog/serviceLayer.html
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from rest_framework.exceptions import NotFound, ValidationError

from apps.orders.models.order import OrderStatus
from apps.payments.constants import (
    DEFAULT_PAYMENT_PROVIDER,
    MAX_PAYMENT_AMOUNT,
    MIN_PAYMENT_AMOUNT,
    PAYMENT_EVENT_CANCELLED,
    PAYMENT_EVENT_CONFIRMED,
    PAYMENT_EVENT_CREATED,
    PAYMENT_EVENT_ERROR,
    PAYMENT_EVENT_REFUND_COMPLETED,
    PAYMENT_EVENT_REFUND_INITIATED,
    PAYMENT_EVENT_STATUS_CHANGED,
    PAYMENT_EVENT_WEBHOOK_RECEIVED,
    PAYMENT_METHOD_CARD,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_PROCESSING,
    PAYMENT_STATUS_REFUNDED,
    PAYMENT_STATUS_SUCCEEDED,
    PAYMENT_STATUS_TRANSITIONS,
)
from apps.payments.models import Payment, PaymentEvent

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Бизнес-логика платежей.

    Все mutating-методы обёрнуты в transaction.atomic и используют
    select_for_update() для исключения race conditions.
    """

    # ==============================================================
    # СОЗДАНИЕ ПЛАТЕЖА
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def create_payment(
        order,
        user,
        amount: Decimal,
        method: str = PAYMENT_METHOD_CARD,
        provider: str = DEFAULT_PAYMENT_PROVIDER,
        note: str = '',
    ) -> Payment:
        """
        Создаёт новый платёж для заказа.

        АЛГОРИТМ:
          1. Проверить что заказ принадлежит пользователю
          2. Проверить что заказ в статусе PENDING (можно оплатить)
          3. Проверить сумму (в пределах лимитов)
          4. Создать Payment (PENDING)
          5. Создать PaymentEvent(CREATED)

        ЗАЩИТА ОТ:
          • Оплата чужого заказа (ownership check)
          • Повторная оплата уже оплаченного заказа
          • Слишком маленькая/большая сумма

        📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/
        """
        # ── Проверка ownership ──
        if order.user_id != user.pk:
            raise NotFound('Заказ не найден.')

        # ── Проверка статуса заказа ──
        # Оплачивать можно только PENDING-заказы.
        # CONFIRMED → уже оплачен. CANCELLED → нельзя оплатить.
        if order.status != OrderStatus.PENDING:
            raise ValidationError({
                'detail': (
                    f'Нельзя создать платёж для заказа в статусе '
                    f'«{order.get_status_display()}». '
                    f'Допускается только «Ожидает оплаты».'
                ),
            })

        # ── Проверка суммы ──
        if amount < MIN_PAYMENT_AMOUNT:
            raise ValidationError({
                'amount': (
                    f'Минимальная сумма платежа — {MIN_PAYMENT_AMOUNT}₽.'
                ),
            })
        if amount > MAX_PAYMENT_AMOUNT:
            raise ValidationError({
                'amount': (
                    f'Максимальная сумма платежа — {MAX_PAYMENT_AMOUNT}₽.'
                ),
            })

        # ── Проверка: сумма платежа должна совпадать с суммой заказа ──
        # 🔴 КРИТИЧЕСКАЯ БЕЗОПАСНОСТЬ: без этой проверки злоумышленник
        # может создать платёж на 1₽ для заказа на 100000₽ → товар за 1₽.
        # 📖 https://owasp.org/www-community/attacks/Business_Logic_Vulnerabilities
        if amount != order.total:
            raise ValidationError({
                'amount': (
                    f'Сумма платежа ({amount}₽) не совпадает с суммой заказа '
                    f'({order.total}₽). Оплатите полную сумму.'
                ),
            })

        # ── Проверка: нет ли уже успешного платежа ──
        existing_paid = Payment.objects.filter(
            order=order,
            status=PAYMENT_STATUS_SUCCEEDED,
        ).exists()
        if existing_paid:
            raise ValidationError({
                'detail': 'Заказ уже оплачен.',
            })

        # ── Создание платежа ──
        payment = Payment(
            order=order,
            user=user,
            amount=amount,
            method=method,
            provider=provider,
            status=PAYMENT_STATUS_PENDING,
            note=note,
            # Генерируем mock external_id (в реальном проекте —
            # от провайдера после API-вызова)
            external_id=f'mock_{uuid.uuid4().hex[:16]}',
        )
        payment.save()

        # ── Аудит: создаём событие ──
        PaymentEvent.objects.create(
            payment=payment,
            event_type=PAYMENT_EVENT_CREATED,
            new_status=PAYMENT_STATUS_PENDING,
            performed_by=user,
            note=f'Платёж {payment.order_number} создан для заказа {order.order_number}',
        )

        logger.info(
            'payment_created',
            extra={
                'payment_id': payment.pk,
                'payment_number': payment.order_number,
                'order_id': order.pk,
                'amount': str(amount),
                'method': method,
            },
        )

        return payment

    # ==============================================================
    # ОБРАБОТКА ПЛАТЕЖА (переход в PROCESSING)
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def process_payment(payment: Payment, *, user=None) -> Payment:
        """
        Переводит платёж в PROCESSING (отправка провайдеру).

        В реальном проекте здесь — вызов API платёжного провайдера:
          yookassa.create_payment(amount, ...)

        Для mock — просто меняем статус.
        """
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        if payment.status != PAYMENT_STATUS_PENDING:
            raise ValidationError({
                'detail': (
                    f'Нельзя обработать платёж в статусе '
                    f'«{payment.get_status_display()}».'
                ),
            })

        old_status = payment.status
        payment.status = PAYMENT_STATUS_PROCESSING
        payment.save(update_fields=['status', 'updated_at'])

        PaymentEvent.objects.create(
            payment=payment,
            event_type=PAYMENT_EVENT_STATUS_CHANGED,
            old_status=old_status,
            new_status=PAYMENT_STATUS_PROCESSING,
            performed_by=user,
        )

        logger.info(
            'payment_processing',
            extra={'payment_id': payment.pk},
        )

        return payment

    # ==============================================================
    # ПОДТВЕРЖДЕНИЕ ОПЛАТЫ (webhook / callback от провайдера)
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def confirm_payment(
        payment: Payment,
        *,
        external_id: str = '',
        payload: dict | None = None,
    ) -> Payment:
        """
        Подтверждает успешную оплату.

        ВЫЗЫВАЕТСЯ ПРИ:
          • Вебхук от платёжного провайдера (YooKassa: payment.succeeded)
          • Callback при возврате пользователя на сайт
          • Ручное подтверждение (admin)

        ПОСЛЕДСТВИЯ:
          • Payment.status → SUCCEEDED
          • Payment.paid_at → now()
          • Order.status → CONFIRMED (через OrderService.confirm)

        АЛГОРИТМ:
          1. select_for_update — блокировка
          2. Валидация перехода (PROCESSING → SUCCEEDED)
          3. Обновление статуса и paid_at
          4. Создание PaymentEvent
          5. Подтверждение заказа (OrderService.confirm)

        📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/
        """
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        # Валидация перехода: допускаем PROCESSING и PENDING
        # (некоторые провайдеры мгновенно отвечают SUCCEEDED)
        allowed = PAYMENT_STATUS_TRANSITIONS.get(payment.status, [])
        if PAYMENT_STATUS_SUCCEEDED not in allowed:
            # Особый случай: если уже SUCCEEDED — идемпотентно возвращаем
            if payment.status == PAYMENT_STATUS_SUCCEEDED:
                logger.info(
                    'payment_already_confirmed',
                    extra={'payment_id': payment.pk},
                )
                return payment
            raise ValidationError({
                'detail': (
                    f'Нельзя подтвердить платёж в статусе '
                    f'«{payment.get_status_display()}».'
                ),
            })

        old_status = payment.status
        payment.status = PAYMENT_STATUS_SUCCEEDED
        payment.paid_at = timezone.now()

        if external_id:
            payment.external_id = external_id
        if payload:
            payment.metadata.update(payload)

        payment.save(update_fields=[
            'status', 'paid_at', 'external_id', 'metadata', 'updated_at',
        ])

        # Аудит
        PaymentEvent.objects.create(
            payment=payment,
            event_type=PAYMENT_EVENT_CONFIRMED,
            old_status=old_status,
            new_status=PAYMENT_STATUS_SUCCEEDED,
            payload=payload or {},
            external_event_id=external_id,
        )

        # ── Подтверждаем заказ ──
        from apps.orders.services.order_service import OrderService
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from django.db import DatabaseError

        try:
            OrderService.confirm(payment.order)
        except (DRFValidationError, DatabaseError) as exc:
            # DRFValidationError: заказ уже подтверждён, неверный статус и т.д.
            # DatabaseError: проблемы с БД (connection, constraint и т.д.)
            # НЕ ловим Exception — KeyboardInterrupt, SystemExit и прочие
            # должны пробрасываться наверх.
            logger.error(
                'payment_confirmed_but_order_failed',
                extra={
                    'payment_id': payment.pk,
                    'order_id': payment.order_id,
                    'error': str(exc),
                },
            )
            # Не откатываем платёж — деньги получены.
            # Order застрянет в PENDING → ручная разбирка.

        logger.info(
            'payment_confirmed',
            extra={
                'payment_id': payment.pk,
                'order_id': payment.order_id,
                'amount': str(payment.amount),
            },
        )

        return payment

    # ==============================================================
    # ОШИБКА ОПЛАТЫ
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def fail_payment(
        payment: Payment,
        *,
        payload: dict | None = None,
        note: str = '',
    ) -> Payment:
        """
        Отмечает платёж как FAILED (оплата отклонена).

        ВЫЗЫВАЕТСЯ ПРИ:
          • Вебхук от провайдера: payment.failed / payment.rejected
          • Таймаут при обработке
          • Fraud detection
        """
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        allowed = PAYMENT_STATUS_TRANSITIONS.get(payment.status, [])
        if PAYMENT_STATUS_FAILED not in allowed:
            raise ValidationError({
                'detail': (
                    f'Нельзя отметить как FAILED платёж в статусе '
                    f'«{payment.get_status_display()}».'
                ),
            })

        old_status = payment.status
        payment.status = PAYMENT_STATUS_FAILED
        if note:
            payment.note = note
        if payload:
            payment.metadata.update(payload)
        payment.save(update_fields=['status', 'note', 'metadata', 'updated_at'])

        PaymentEvent.objects.create(
            payment=payment,
            event_type=PAYMENT_EVENT_ERROR,
            old_status=old_status,
            new_status=PAYMENT_STATUS_FAILED,
            payload=payload or {},
            note=note or 'Оплата отклонена',
        )

        logger.info(
            'payment_failed',
            extra={
                'payment_id': payment.pk,
                'note': note,
            },
        )

        return payment

    # ==============================================================
    # ОТМЕНА ПЛАТЕЖА
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def cancel_payment(
        payment: Payment,
        *,
        user=None,
        note: str = '',
    ) -> Payment:
        """
        Отменяет платёж.

        ВЫЗЫВАЕТСЯ ПРИ:
          • Пользователь нажал «Отменить» на странице оплаты
          • Таймаут неоплачённого платежа (management command)
          • Админ отменил вручную
        """
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        allowed = PAYMENT_STATUS_TRANSITIONS.get(payment.status, [])
        if PAYMENT_STATUS_CANCELLED not in allowed:
            raise ValidationError({
                'detail': (
                    f'Нельзя отменить платёж в статусе '
                    f'«{payment.get_status_display()}».'
                ),
            })

        old_status = payment.status
        payment.status = PAYMENT_STATUS_CANCELLED
        payment.cancelled_at = timezone.now()
        if note:
            payment.note = note
        payment.save(update_fields=[
            'status', 'cancelled_at', 'note', 'updated_at',
        ])

        PaymentEvent.objects.create(
            payment=payment,
            event_type=PAYMENT_EVENT_CANCELLED,
            old_status=old_status,
            new_status=PAYMENT_STATUS_CANCELLED,
            performed_by=user,
            note=note or 'Платёж отменён',
        )

        logger.info(
            'payment_cancelled',
            extra={
                'payment_id': payment.pk,
                'cancelled_by': getattr(user, 'pk', None),
            },
        )

        return payment

    # ==============================================================
    # ВОЗВРАТ СРЕДСТВ
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def refund_payment(
        payment: Payment,
        *,
        amount: Decimal | None = None,
        reason: str = '',
        user=None,
    ) -> Payment:
        """
        Оформляет возврат средств.

        АЛГОРИТМ:
          1. Проверить что платёж SUCCEEDED
          2. Определить сумму возврата (вся или частичная)
          3. Обновить refund_amount
          4. Если refund_amount == amount → REFUNDED
          5. Создать PaymentEvent

        ПОЧЕМУ ПОДДЕРЖИВАЕМ ЧАСТИЧНЫЙ ВОЗВРАТ:
          • Возврат одной позиции из заказа (не всего заказа)
          • Частичный refund при повреждении товара
        """
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        if payment.status != PAYMENT_STATUS_SUCCEEDED:
            raise ValidationError({
                'detail': (
                    f'Возврат возможен только для оплаченного платежа. '
                    f'Текущий статус: «{payment.get_status_display()}».'
                ),
            })

        # Сумма возврата: если не указана — полная (amount)
        refund_amount = amount if amount is not None else payment.amount

        if refund_amount <= 0:
            raise ValidationError({
                'amount': 'Сумма возврата должна быть > 0.',
            })

        new_total_refund = payment.refund_amount + refund_amount
        if new_total_refund > payment.amount:
            raise ValidationError({
                'amount': (
                    f'Сумма возврата ({new_total_refund}₽) превышает '
                    f'сумму платежа ({payment.amount}₽).'
                ),
            })

        old_status = payment.status
        payment.refund_amount = new_total_refund
        payment.refund_reason = reason

        # Если вернули всю сумму → REFUNDED
        if new_total_refund >= payment.amount:
            payment.status = PAYMENT_STATUS_REFUNDED
            payment.refunded_at = timezone.now()

        payment.save(update_fields=[
            'status', 'refund_amount', 'refund_reason',
            'refunded_at', 'updated_at',
        ])

        # Аудит
        event_type = (
            PAYMENT_EVENT_REFUND_COMPLETED
            if payment.status == PAYMENT_STATUS_REFUNDED
            else PAYMENT_EVENT_REFUND_INITIATED
        )
        PaymentEvent.objects.create(
            payment=payment,
            event_type=event_type,
            old_status=old_status,
            new_status=payment.status,
            performed_by=user,
            payload={'refund_amount': str(refund_amount)},
            note=reason or f'Возврат {refund_amount}₽',
        )

        logger.info(
            'payment_refunded',
            extra={
                'payment_id': payment.pk,
                'refund_amount': str(refund_amount),
                'total_refunded': str(new_total_refund),
                'new_status': payment.status,
            },
        )

        return payment

    # ==============================================================
    # ОБРАБОТКА ВЕБХУКА
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def handle_webhook(
        *,
        external_id: str,
        event_type: str,
        status: str,
        payload: dict | None = None,
    ) -> Payment | None:
        """
        Обрабатывает вебхук от платёжного провайдера.

        ВЫЗЫВАЕТСЯ ПРИ:
          • POST /api/v1/payments/webhook/ (внешний запрос от провайдера)

        АЛГОРИТМ:
          1. Найти платёж по external_id
          2. Записать PaymentEvent(WEBHOOK_RECEIVED)
          3. Обработать статус:
             - succeeded → confirm_payment()
             - failed → fail_payment()
             - cancelled → cancel_payment()
          4. Вернуть обновлённый платёж

        ИДЕМПОТЕНТНОСТЬ:
          Если вебхук пришёл дважды — обрабатываем корректно:
          • Уже SUCCEEDED → возвращаем без ошибки
          • Для каждого вебхука создаётся PaymentEvent

        📖 https://en.wikipedia.org/wiki/Idempotence
        """
        # ── Ищем платёж по external_id ──
        try:
            payment = Payment.objects.with_external_id(external_id).first()
        except Exception:
            payment = None

        if payment is None:
            logger.warning(
                'webhook_payment_not_found',
                extra={'external_id': external_id},
            )
            return None

        # ── Записываем вебхук в аудит-лог ──
        PaymentEvent.objects.create(
            payment=payment,
            event_type=PAYMENT_EVENT_WEBHOOK_RECEIVED,
            payload=payload or {},
            external_event_id=external_id,
            note=f'Webhook: event={event_type}, status={status}',
        )

        # ── Обрабатываем статус ──
        if status == PAYMENT_STATUS_SUCCEEDED:
            payment = PaymentService.confirm_payment(
                payment,
                external_id=external_id,
                payload=payload,
            )
        elif status == PAYMENT_STATUS_FAILED:
            payment = PaymentService.fail_payment(
                payment,
                payload=payload,
            )
        elif status == PAYMENT_STATUS_CANCELLED:
            payment = PaymentService.cancel_payment(
                payment,
                note='Отменён провайдером (webhook)',
            )
        else:
            logger.warning(
                'webhook_unknown_status',
                extra={
                    'external_id': external_id,
                    'status': status,
                },
            )

        return payment

    # ==============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==============================================================

    @staticmethod
    def get_payment_by_number(payment_number: str) -> Payment:
        """
        Возвращает платёж по номеру (PAY-000001).
        Бросает NotFound если не найден.
        """
        try:
            return Payment.objects.get(order_number=payment_number)
        except Payment.DoesNotExist:
            raise NotFound('Платёж не найден.')

    @staticmethod
    def get_payment_for_order_check(order, user) -> Payment:
        """
        Возвращает платёж для проверки ownership.
        """
        try:
            payment = Payment.objects.get(order=order, user=user)
        except Payment.DoesNotExist:
            raise NotFound('Платёж не найден.')
        return payment
