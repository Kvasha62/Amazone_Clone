# ────────────────────────────────────────────────────────────────────────
# apps/orders/services/order_service.py — бизнес-логика заказов.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Service Layer» (сервисный слой):
#   View → сериализатор (валидация) → сервис (бизнес-логика) → ORM (SQL)
#
#   View НЕ знает про:
#     • transaction.atomic (транзакции)
#     • select_for_update (пессимистичные блокировки)
#     • проверку стока, лимитов, статусов
#     • генерацию номера заказа
#     • расчёт суммы
#   Всё инкапсулировано в сервисе.
#
# БЕЗОПАСНОСТЬ КОНКУРЕНТНОГО ДОСТУПА:
#   Все mutating-методы используют:
#     1. @transaction.atomic — атомарные транзакции
#     2. select_for_update() — пессимистичная блокировка строк
#     3. UniqueConstraint — защита от дублей на уровне БД
#
# ОПЕРАЦИИ:
#   create_from_cart()   — создать заказ из корзины
#   confirm()            — подтвердить (оплачено)
#   cancel()             — отменить
#   transition_status()  — общий метод перехода статуса
#
# 📖 Про Service Layer: https://martinfowler.com/eaaCatalog/serviceLayer.html
# 📖 Про select_for_update: https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
# 📖 Про transaction.atomic: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Все API views заказов → ImportError
#   • POST /api/v1/orders/ → 500
#   • Оформление заказа невозможно
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import models, transaction
from django.db.models import F
from django.utils import timezone

from rest_framework.exceptions import NotFound, ValidationError

from apps.cart.models import Cart, CartItem
from apps.orders.constants import (
    CANCELLATION_REASONS,
    MAX_ITEM_QUANTITY,
    MAX_ORDER_ITEMS,
    MIN_ORDER_TOTAL,
    ORDER_PENDING_TTL_HOURS,
)
from apps.orders.models import Order, OrderItem
from apps.orders.models.order import (
    ORDER_STATUS_TRANSITIONS,
    OrderStatus,
)

logger = logging.getLogger(__name__)


class OrderService:
    """
    Бизнес-логика заказов.

    View не знает про транзакции, select_for_update, генерацию номеров —
    всё инкапсулировано здесь.

    Все mutating-методы обёрнуты в transaction.atomic и используют
    пессимистичные блокировки (select_for_update), чтобы исключить
    race conditions при параллельных запросах.

    Исключения: бросаем DRF-исключения (NotFound, ValidationError),
    чтобы view'хи могли прокинуть их в Response без лишних try/except.

    📖 https://martinfowler.com/eaaCatalog/serviceLayer.html
    """

    # ==============================================================
    # СОЗДАНИЕ ЗАКАЗА ИЗ КОРЗИНЫ
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def create_from_cart(
        user,
        cart: Cart,
        *,
        delivery_cost=0,
        notes: str = '',
    ) -> Order:
        """
        Создаёт заказ из активной корзины.

        АЛГОРИТМ (10 шагов):
          0. Проверить что корзина активна и принадлежит пользователю
          1. Загрузить корзину с prefetch + select_for_update
          2. Проверить наличие товаров в корзине
          3. Проверить лимит позиций (MAX_ORDER_ITEMS)
          4. Получить адрес по умолчанию (или None)
          5. Создать Order (snapshot адреса, суммы)
          6. Создать OrderItem (snapshot цен и названий)
          7. Пересчитать итоговую сумму
          8. Проверить MIN_ORDER_TOTAL
          9. Деактивировать корзину
         10. Вернуть заказ

        ЗАЩИТА ОТ:
          • Пустой корзины (ValidationError)
          • Превышения лимита позиций (ValidationError)
          • Неактивных вариантов (пропускаются)
          • Товаров без цены (пропускаются)
          • Суммы < MIN_ORDER_TOTAL (ValidationError)
          • Race conditions (select_for_update)
          • IDOR: корзина чужая → NotFound

        ПОЧЕМУ SNAPSHOT ЦЕН, А НЕ FK:
          Цены меняются. Заказ — immutable document.
          Если цена изменилась после оформления →
          сумма заказа должна остаться прежней.
          Поэтому копируем price.effective_price в OrderItem.unit_price.

        📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
        """
        from decimal import Decimal

        # ── Шаг 0: Проверка ownership ──
        # Корзина должна принадлежать пользователю.
        # cart.user_id (integer) — без SQL.
        # cart.user — SQL-запрос → используем user_id!
        if cart.user_id != user.pk:
            raise NotFound('Корзина не найдена.')

        if not cart.is_active:
            raise NotFound('Корзина не найдена.')

        # ── Шаг 1: Загрузка корзины с блокировкой ──
        # select_for_update() — блокируем корзину до COMMIT.
        # Две параллельные попытки оформить одну корзину →
        # вторая будет ждать.
        cart = (
            Cart.objects
            .select_for_update()
            .prefetch_related(
                'items',
                'items__variant',
                'items__variant__product',
                'items__variant__price',
            )
            .get(pk=cart.pk)
        )

        items = list(cart.items.all())

        # ── Шаг 2: Проверка наличия товаров ──
        if not items:
            raise ValidationError({
                'detail': 'Невозможно оформить заказ из пустой корзины.',
            })

        # ── Шаг 3: Фильтрация невалидных позиций ──
        # Пропускаем:
        #   • Неактивные варианты (variant.is_active = False)
        #   • Варианты без цены (variant.price = None)
        from apps.catalog.constants import ProductStatus

        valid_items: list[CartItem] = []
        for item in items:
            variant = item.variant

            # Вариант деактивирован → пропускаем
            if not variant or not variant.is_active:
                logger.debug(
                    'order_skip_variant_inactive',
                    extra={'variant_id': item.variant_id},
                )
                continue

            # Товар недоступен → пропускаем
            if variant.product.status != ProductStatus.ACTIVE:
                logger.debug(
                    'order_skip_product_unavailable',
                    extra={'product_id': variant.product_id},
                )
                continue

            # Нет цены → пропускаем (бесплатных товаров не бывает)
            price_obj = getattr(variant, 'price', None)
            if price_obj is None:
                logger.debug(
                    'order_skip_no_price',
                    extra={'variant_id': item.variant_id},
                )
                continue

            valid_items.append(item)

        if not valid_items:
            raise ValidationError({
                'detail': 'Нет доступных для заказа товаров в корзине.',
            })

        # ── Проверка лимита позиций ──
        if len(valid_items) > MAX_ORDER_ITEMS:
            raise ValidationError({
                'detail': (
                    f'Максимум позиций в заказе — {MAX_ORDER_ITEMS}. '
                    f'У вас {len(valid_items)}.'
                ),
            })

        # ── Шаг 4: Получить адрес доставки ──
        # Ищем is_default=True. Если нет — берём последний созданный.
        address = (
            user.addresses
            .filter(is_default=True)
            .first()
        )
        if address is None:
            # Нет адреса по умолчанию → берём любой
            address = user.addresses.first()

        if address is None:
            raise ValidationError({
                'detail': 'Добавьте адрес доставки перед оформлением заказа.',
            })

        # ── Шаг 5: Создание Order ──
        delivery_cost_decimal = Decimal(str(delivery_cost))

        # Вычисляем порядковый номер для генерации order_number.
        # ── ЗАЩИТА ОТ RACE CONDITION ──
        # MAX()+1 — уязвим при параллельных запросах:
        #   Транзакция A: MAX()=99 → next_seq=100
        #   Транзакция B: MAX()=99 → next_seq=100 (КОНФЛИКТ!)
        # UniqueConstraint на _order_number_seq поймает дубль,
        # но без retry — IntegrityError провалит всю транзакцию.
        #
        # РЕШЕНИЕ: retry-цикл. При IntegrityError пересчитываем MAX().
        # После 3 попыток — отдаём ошибку наверх (катастрофический случай).
        #
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#get-or-create
        from django.db import IntegrityError
        from apps.orders.constants import ORDER_NUMBER_PREFIX, ORDER_NUMBER_DIGITS

        order = None
        for _attempt in range(3):
            max_seq = Order.objects.aggregate(
                max_seq=models.Max('_order_number_seq'),
            )['max_seq'] or 0
            next_seq = max_seq + 1

            order = Order(
                user=user,
                cart=cart,
                status=OrderStatus.PENDING,
                _order_number_seq=next_seq,

                # Snapshot адреса
                recipient_name=address.recipient_name,
                country=address.country,
                region=address.region,
                city=address.city,
                street=address.street,
                postal_code=address.postal_code,

                # Суммы (пересчитаются ниже)
                subtotal=Decimal('0.00'),
                delivery_cost=delivery_cost_decimal,
                discount=Decimal('0.00'),
                total=Decimal('0.00'),

                notes=notes,
            )
            order.order_number = (
                f'{ORDER_NUMBER_PREFIX}-{next_seq:0{ORDER_NUMBER_DIGITS}d}'
            )
            try:
                order.save()
                break  # Успех — выходим из retry-цикла
            except IntegrityError:
                # Параллельный заказ занял этот seq — пробуем снова
                logger.warning(
                    'order_number_collision_retry',
                    extra={'attempt': _attempt + 1, 'next_seq': next_seq},
                )
                continue
        else:
            # 3 попытки исчерпаны — откатываем всю транзакцию
            raise ValidationError({
                'detail': 'Не удалось создать номер заказа. Попробуйте снова.',
            })

        # ── Шаг 6: Создание OrderItem (snapshot) ──
        order_items_bulk = []
        for cart_item in valid_items:
            variant = cart_item.variant
            price_obj = variant.price
            effective_price = price_obj.effective_price

            order_items_bulk.append(OrderItem(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                sku=variant.sku,
                unit_price=effective_price,
                quantity=cart_item.quantity,
            ))

        # bulk_create — один INSERT для всех позиций.
        # Быстрее чем N отдельных create().
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-create
        OrderItem.objects.bulk_create(order_items_bulk)

        # ── Шаг 7: Пересчёт итоговой суммы ──
        order.recalculate_total()
        order.save(update_fields=['subtotal', 'total', 'updated_at'])

        # ── Шаг 8: Проверка MIN_ORDER_TOTAL ──
        if order.total < MIN_ORDER_TOTAL:
            # Откатываем заказ (DELETE) — слишком маленькая сумма.
            # transaction.atomic откатит и Order, и OrderItem.
            raise ValidationError({
                'detail': (
                    f'Минимальная сумма заказа — {MIN_ORDER_TOTAL}₽. '
                    f'Текущая сумма: {order.total}₽.'
                ),
            })

        # ── Шаг 9: Деактивация корзины ──
        # Корзина «использована» — деактивируем (не удаляем!).
        # Аналитика: «сколько корзин → заказов» (conversion rate).
        cart.is_active = False
        cart.save(update_fields=['is_active', 'updated_at'])

        logger.info(
            'order_created',
            extra={
                'order_id': order.pk,
                'order_number': order.order_number,
                'user_id': user.pk,
                'total': str(order.total),
                'items_count': len(order_items_bulk),
            },
        )

        return order

    # ==============================================================
    # ПЕРЕХОД СТАТУСА (Finite State Machine)
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def transition_status(
        order: Order,
        new_status: str,
        *,
        user=None,
    ) -> Order:
        """
        Переводит заказ в новый статус по правилам FSM.

        ПРАВИЛА (ORDER_STATUS_TRANSITIONS):
          PENDING    → [CONFIRMED, CANCELLED]
          CONFIRMED  → [PROCESSING, CANCELLED]
          PROCESSING → [SHIPPED, CANCELLED]
          SHIPPED    → [DELIVERED, CANCELLED]
          DELIVERED  → []  (терминальный)
          CANCELLED  → []  (терминальный)

        ВЫБРАСЫВАЕТ:
          ValidationError — если переход недопустим

        ПОБОЧНЫЕ ЭФФЕКТЫ:
          • CONFIRMED → устанавливает confirmed_at
          • CANCELLED → устанавливает cancelled_at
          • DELIVERED → устанавливает delivered_at

        📖 https://en.wikipedia.org/wiki/Finite-state_machine
        """
        # select_for_update — блокируем заказ до COMMIT.
        # Два менеджера одновременно подтверждают один заказ →
        # второй будет ждать.
        order = (
            Order.objects
            .select_for_update()
            .get(pk=order.pk)
        )

        current_status = order.status

        # ── Проверка терминального статуса ──
        if order.is_terminal:
            raise ValidationError({
                'detail': (
                    f'Заказ {order.order_number} в терминальном статусе '
                    f'«{order.get_status_display()}». '
                    f'Дальнейшие переходы невозможны.'
                ),
            })

        # ── Проверка допустимости перехода ──
        allowed = ORDER_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValidationError({
                'detail': (
                    f'Переход «{current_status} → {new_status}» недопустим. '
                    f'Допустимые: {[s for s in allowed]}'
                ),
            })

        # ── Применяем переход ──
        order.status = new_status

        # ── Таймстампы переходов ──
        now = timezone.now()
        if new_status == OrderStatus.CONFIRMED:
            order.confirmed_at = now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now

        order.save(update_fields=[
            'status',
            'confirmed_at',
            'delivered_at',
            'cancelled_at',
            'updated_at',
        ])

        # ── Интеграция с inventory (reserve/release/commit) ──
        # После успешного перехода вызываем соответствующие методы
        # InventoryService для управления стоком.
        # Оборачиваем в try/except чтобы ошибка стока не ломала
        # переход статуса (особенно для заказов без items).
        OrderService._handle_inventory_transition(order, new_status)

        logger.info(
            'order_status_changed',
            extra={
                'order_id': order.pk,
                'order_number': order.order_number,
                'old_status': current_status,
                'new_status': new_status,
                'changed_by': getattr(user, 'pk', None),
            },
        )

        return order

    # ==============================================================
    # ИНТЕГРАЦИЯ С INVENTORY
    # ==============================================================

    @staticmethod
    def _handle_inventory_transition(order: Order, new_status: str) -> None:
        """
        Вызывает методы InventoryService при переходе статуса.

        ПРАВИЛА:
          • CONFIRMED  → reserve_stock()  — резервирование стока
          • CANCELLED  → release_stock()  — освобождение резерва
          • DELIVERED  → commit_stock()   — физическое списание

        ПОЧЕМУ TRY/EXCEPT, А НЕ ЖЁСТКАЯ СВЯЗКА:
          1) Заказ может быть создан БЕЗ OrderItem (тесты, manual order)
             → reserve_stock() вернёт [] — это нормально.
          2) InventoryService.reserve_stock() может бросить
             ValidationError («недостаточно стока»).
             В этом случае логируем ошибку, но НЕ откатываем статус.
             Причина: платёж уже прошёл — откат creates inconsistency.
             Решение: ручная разбирка (admin panel).
          3) Тестовые заказы (через create_test_order) не имеют
             реальных variant → stock может не существовать.

        📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/
        """
        from apps.inventory.services.inventory_service import InventoryService

        try:
            if new_status == OrderStatus.CONFIRMED:
                movements = InventoryService.reserve_stock(order)
                if movements:
                    logger.info(
                        'inventory_reserved_on_confirm',
                        extra={
                            'order_id': order.pk,
                            'movements_count': len(movements),
                        },
                    )

            elif new_status == OrderStatus.CANCELLED:
                movements = InventoryService.release_stock(order)
                if movements:
                    logger.info(
                        'inventory_released_on_cancel',
                        extra={
                            'order_id': order.pk,
                            'movements_count': len(movements),
                        },
                    )

            elif new_status == OrderStatus.DELIVERED:
                movements = InventoryService.commit_stock(order)
                if movements:
                    logger.info(
                        'inventory_committed_on_deliver',
                        extra={
                            'order_id': order.pk,
                            'movements_count': len(movements),
                        },
                    )

        except Exception as exc:
            # Логируем ошибку, но не откатываем транзакцию.
            # Причина: статус уже изменён, платёж проведён (если CONFIRMED).
            # Откат = inconsistency между payment и order status.
            # Решение: ручная разбирка через admin + audit log.
            logger.error(
                'inventory_transition_error',
                extra={
                    'order_id': order.pk,
                    'order_number': order.order_number,
                    'new_status': new_status,
                    'error': str(exc),
                },
            )

    # ==============================================================
    # ПОДТВЕРЖДЕНИЕ ЗАКАЗА (оплата прошла)
    # ==============================================================

    @staticmethod
    def confirm(order: Order, *, user=None) -> Order:
        """
        Переводит заказ из PENDING в CONFIRMED.
        Вызывается после успешной оплаты (payment webhook / callback).

        ПОСЛЕДСТВИЯ:
          • confirmed_at = now()
          • Сток должен быть зарезервирован/списан (inventory app)
          • Уведомление пользователю (email/push)
        """
        return OrderService.transition_status(
            order, OrderStatus.CONFIRMED, user=user,
        )

    # ==============================================================
    # ОТМЕНА ЗАКАЗА
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def cancel(
        order: Order,
        *,
        reason: str = '',
        user=None,
    ) -> Order:
        """
        Отменяет заказ с указанием причины.

        ВАЛИДАЦИЯ:
          • reason не должен быть пустым (извлекаем из constants)
          • Заказ не должен быть в терминальном статусе

        ПОСЛЕДСТВИЯ:
          • cancelled_at = now()
          • Сток должен быть освобождён (inventory app)
          • Возврат средств (payment app)
          • Уведомление пользователю

        📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/
        """
        # Валидация причины
        valid_reasons = [r[0] for r in CANCELLATION_REASONS]
        if reason and reason not in valid_reasons:
            raise ValidationError({
                'reason': f'Недопустимая причина отмены: {reason}',
            })

        order = OrderService.transition_status(
            order, OrderStatus.CANCELLED, user=user,
        )

        # Сохраняем причину отмены
        order.cancellation_reason = reason
        order.save(update_fields=['cancellation_reason', 'updated_at'])

        # ── Возврат средств (payment app) ──
        # Если заказ был оплачен (CONFIRMED → CANCELLED),
        # инициируем возврат через PaymentService.
        # Оборачиваем в try/except — ошибка возврата не должна
        # откатывать отмену заказа (товар уже не будет доставлен).
        from apps.payments.models import Payment
        from apps.payments.constants import PAYMENT_STATUS_SUCCEEDED

        succeeded_payments = Payment.objects.filter(
            order=order,
            status=PAYMENT_STATUS_SUCCEEDED,
        )
        if succeeded_payments.exists():
            try:
                from apps.payments.services.payment_service import PaymentService
                for payment in succeeded_payments:
                    PaymentService.refund_payment(
                        payment,
                        reason=f'Отмена заказа {order.order_number}: {reason}',
                        user=user,
                    )
                    logger.info(
                        'order_cancel_refund_initiated',
                        extra={
                            'order_id': order.pk,
                            'payment_id': payment.pk,
                            'refund_amount': str(payment.amount),
                        },
                    )
            except Exception as exc:
                logger.error(
                    'order_cancel_refund_failed',
                    extra={
                        'order_id': order.pk,
                        'error': str(exc),
                    },
                )
                # Не откатываем отмену — возврат можно сделать вручную.

        logger.info(
            'order_cancelled',
            extra={
                'order_id': order.pk,
                'order_number': order.order_number,
                'reason': reason,
                'cancelled_by': getattr(user, 'pk', None),
            },
        )

        return order

    # ==============================================================
    # СТАТИСТИКА / АГРЕГАЦИЯ
    # ==============================================================

    @staticmethod
    def get_user_order_summary(user) -> dict:
        """
        Возвращает сводку по заказам пользователя.

        ПРИМЕР ОТВЕТА:
          {
              'total_orders': 15,
              'active_orders': 3,
              'total_spent': '125000.00',
          }

        Используется в профиле пользователя и dashboard.
        """
        from django.db.models import Count, Q, Sum

        qs = Order.objects.for_user(user)

        stats = qs.aggregate(
            total_orders=Count('id'),
            active_orders=Count(
                'id',
                filter=~Q(
                    status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED],
                ),
            ),
            total_spent=Sum(
                'total',
                filter=Q(status=OrderStatus.DELIVERED),
            ),
        )

        return {
            'total_orders': stats['total_orders'] or 0,
            'active_orders': stats['active_orders'] or 0,
            'total_spent': stats['total_spent'] or '0.00',
        }
