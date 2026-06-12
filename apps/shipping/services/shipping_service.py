# ────────────────────────────────────────────────────────────────────────
# apps/shipping/services/shipping_service.py — бизнес-логика доставки.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Service Layer»:
#   View → сериализатор (валидация) → сервис (бизнес-логика) → ORM (SQL)
#
# БЕЗОПАСНОСТЬ КОНКУРЕНТНОГО ДОСТУПА:
#   Все mutating-методы используют:
#     1. @transaction.atomic — атомарные транзакции
#     2. select_for_update() — пессимистичная блокировка строк
#
# ОПЕРАЦИИ:
#   calculate_shipping_cost()  — рассчитать стоимость доставки
#   get_available_methods()    — доступные способы для заказа
#   create_shipment()          — создать отправление для заказа
#   update_tracking()          — обновить трек-номер
#   transition_status()        — перевести отправление в новый статус
#
# 📖 Про Service Layer: https://martinfowler.com/eaaCatalog/serviceLayer.html
# 📖 Про select_for_update: https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Все API views доставки → ImportError
#   • POST /api/v1/shipping/ → 500
#   • Оформление доставки невозможно
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from rest_framework.exceptions import NotFound, ValidationError

from apps.orders.models.order import OrderStatus
from apps.shipping.constants import (
    MAX_SHIPPING_COST,
    SHIPMENT_IN_TRANSIT,
    SHIPMENT_PREPARING,
    SHIPMENT_STATUS_TRANSITIONS,
    SHIPMENT_TERMINAL_STATUSES,
)
from apps.shipping.models import Shipment, ShippingMethod, ShippingZone

logger = logging.getLogger(__name__)


class ShippingService:
    """
    Бизнес-логика доставки.

    View не знает про транзакции, select_for_update, расчёт стоимости —
    всё инкапсулировано здесь.
    """

    # ==============================================================
    # РАСЧЁТ СТОИМОСТИ ДОСТАВКИ
    # ==============================================================

    @staticmethod
    def calculate_shipping_cost(
        order_total: Decimal,
        *,
        zone: ShippingZone | None = None,
        zone_code: str | None = None,
        region: str | None = None,
        shipping_type: str | None = None,
        weight_kg: Decimal | None = None,
    ) -> dict:
        """
        Рассчитывает стоимость доставки для всех доступных способов.

        Определяет зону по region или zone_code, затем фильтрует
        активные способы доставки для этой зоны.

        ARGS:
            order_total: сумма заказа (для проверки бесплатной доставки)
            zone: зона доставки (если известна)
            zone_code: код зоны (альтернатива zone)
            region: название региона (для автоопределения зоны)
            shipping_type: фильтр по типу доставки (опционально)
            weight_kg: вес заказа в кг (опционально)

        RETURNS:
            {
                'zone': ShippingZone | None,
                'methods': [
                    {
                        'method': ShippingMethod,
                        'cost': Decimal,
                    },
                    ...
                ]
            }
        """
        # ── Шаг 1: Определение зоны ──
        # Если zone_code/region были переданы, но зона не найдена →
        # не возвращаем методы (пользователь явно указал зону).
        explicitly_requested = bool(zone_code or region)
        if zone is None:
            zone = ShippingService._resolve_zone(zone_code, region)

        if explicitly_requested and zone is None:
            # Зона запрошена, но не найдена → пустой результат
            return {
                'zone': None,
                'methods': [],
            }

        # ── Шаг 2: Получение способов доставки ──
        methods_qs = ShippingMethod.objects.active().select_related('zone')

        if zone:
            methods_qs = methods_qs.for_zone(zone)
        if shipping_type:
            methods_qs = methods_qs.by_type(shipping_type)

        methods = list(methods_qs)

        # ── Шаг 3: Расчёт стоимости для каждого способа ──
        results = []
        for method in methods:
            cost = method.calculate_cost(order_total, weight_kg)
            results.append({
                'method': method,
                'cost': cost,
            })

        return {
            'zone': zone,
            'methods': results,
        }

    # ==============================================================
    # СПИСОК ДОСТУПНЫХ СПОСОБОВ ДОСТАВКИ
    # ==============================================================

    @staticmethod
    def get_available_methods(
        *,
        zone_code: str | None = None,
        region: str | None = None,
        shipping_type: str | None = None,
    ) -> list[ShippingMethod]:
        """
        Возвращает список доступных способов доставки для зоны.

        ARGS:
            zone_code: код зоны доставки
            region: название региона (альтернатива zone_code)
            shipping_type: фильтр по типу доставки

        RETURNS:
            Список ShippingMethod
        """
        zone = ShippingService._resolve_zone(zone_code, region)

        # Если зона запрошена, но не найдена → пустой список
        if (zone_code or region) and zone is None:
            return []

        qs = ShippingMethod.objects.active().with_zone()
        if zone:
            qs = qs.for_zone(zone)
        if shipping_type:
            qs = qs.by_type(shipping_type)

        return list(qs)

    # ==============================================================
    # СОЗДАНИЕ ОТПРАВЛЕНИЯ
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def create_shipment(
        order,
        method: ShippingMethod,
        *,
        shipping_cost: Decimal | None = None,
        weight_kg: Decimal | None = None,
        notes: str = '',
    ) -> Shipment:
        """
        Создаёт отправление для заказа.

        АЛГОРИТМ:
          1. Проверить что заказ не имеет отправления
          2. Проверить что заказ подтверждён (не PENDING)
          3. Рассчитать стоимость доставки (если не передана)
          4. Создать Shipment

        ARGS:
            order: экземпляр Order
            method: способ доставки
            shipping_cost: стоимость (если None — рассчитывается)
            weight_kg: вес заказа
            notes: примечания

        RETURNS:
            Созданный Shipment

        RAISES:
            ValidationError: если заказ уже имеет отправление
                             или заказ в статусе PENDING
        """
        # ── Шаг 1: Проверка уникальности ──
        if hasattr(order, 'shipment'):
            raise ValidationError({
                'detail': (
                    f'Заказ {order.order_number} уже имеет отправление '
                    f'({order.shipment.internal_tracking}).'
                ),
            })

        # ── Шаг 2: Проверка статуса заказа ──
        if order.status == OrderStatus.PENDING:
            raise ValidationError({
                'detail': (
                    f'Нельзя создать отправление для заказа '
                    f'{order.order_number} в статусе PENDING. '
                    f'Сначала подтвердите заказ.'
                ),
            })

        # ── Шаг 3: Расчёт стоимости ──
        if shipping_cost is None:
            shipping_cost = method.calculate_cost(order.total, weight_kg)

        # ── Шаг 4: Защита от некорректной стоимости ──
        if shipping_cost > MAX_SHIPPING_COST:
            raise ValidationError({
                'detail': (
                    f'Стоимость доставки ({shipping_cost}) превышает '
                    f'максимально допустимую ({MAX_SHIPPING_COST}).'
                ),
            })

        # ── Шаг 5: Создание Shipment ──
        shipment = Shipment(
            order=order,
            user=order.user,
            method=method,
            status=SHIPMENT_PREPARING,
            shipping_cost=shipping_cost,
            weight_kg=weight_kg,
            notes=notes,
        )
        shipment.save()

        logger.info(
            'shipment_created',
            extra={
                'shipment_id': shipment.pk,
                'internal_tracking': shipment.internal_tracking,
                'order_id': order.pk,
                'order_number': order.order_number,
                'method': str(method),
                'shipping_cost': str(shipping_cost),
            },
        )

        return shipment

    # ==============================================================
    # ОБНОВЛЕНИЕ ТРЕК-НОМЕРА
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def update_tracking(
        shipment: Shipment,
        tracking_number: str,
    ) -> Shipment:
        """
        Обновляет трек-номер отправления.

        ARGS:
            shipment: экземпляр Shipment
            tracking_number: трек-номер от службы доставки

        RETURNS:
            Обновлённый Shipment
        """
        shipment = (
            Shipment.objects
            .select_for_update()
            .get(pk=shipment.pk)
        )

        shipment.tracking_number = tracking_number
        shipment.save(update_fields=['tracking_number', 'updated_at'])

        logger.info(
            'shipment_tracking_updated',
            extra={
                'shipment_id': shipment.pk,
                'internal_tracking': shipment.internal_tracking,
                'tracking_number': tracking_number,
            },
        )

        return shipment

    # ==============================================================
    # ПЕРЕХОД СТАТУСА
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def transition_status(
        shipment: Shipment,
        new_status: str,
        *,
        tracking_number: str | None = None,
    ) -> Shipment:
        """
        Переводит отправление в новый статус по правилам FSM.

        ПРАВИЛА (SHIPMENT_STATUS_TRANSITIONS):
          PREPARING      → [IN_TRANSIT, RETURNED]
          IN_TRANSIT     → [OUT_FOR_DELIVERY, FAILED, RETURNED]
          OUT_FOR_DELIVERY → [DELIVERED, FAILED]
          FAILED         → [IN_TRANSIT, RETURNED]
          DELIVERED      → [] (терминальный)
          RETURNED       → [] (терминальный)

        ПОБОЧНЫЕ ЭФФЕКТЫ:
          • IN_TRANSIT → устанавливает shipped_at
          • DELIVERED  → устанавливает delivered_at

        ARGS:
            shipment: экземпляр Shipment
            new_status: новый статус (из SHIPMENT_STATUS_CHOICES)
            tracking_number: обновить трек-номер (опционально)

        RETURNS:
            Обновлённый Shipment

        RAISES:
            ValidationError: если переход недопустим
        """
        # select_for_update — блокируем отправление до COMMIT.
        shipment = (
            Shipment.objects
            .select_for_update()
            .get(pk=shipment.pk)
        )

        current_status = shipment.status

        # ── Проверка терминального статуса ──
        if shipment.is_terminal:
            raise ValidationError({
                'detail': (
                    f'Отправление {shipment.internal_tracking} '
                    f'в терминальном статусе '
                    f'«{shipment.get_status_display()}». '
                    f'Дальнейшие переходы невозможны.'
                ),
            })

        # ── Проверка допустимости перехода ──
        allowed = SHIPMENT_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValidationError({
                'detail': (
                    f'Переход «{current_status} → {new_status}» '
                    f'недопустим. '
                    f'Допустимые: {list(allowed)}'
                ),
            })

        # ── Применяем переход ──
        shipment.status = new_status

        # ── Таймстампы переходов ──
        now = timezone.now()
        if new_status == SHIPMENT_IN_TRANSIT:
            shipment.shipped_at = now
        elif new_status in SHIPMENT_TERMINAL_STATUSES:
            if new_status == 'delivered':
                shipment.delivered_at = now

        # ── Обновление трек-номера (если передан) ──
        if tracking_number:
            shipment.tracking_number = tracking_number

        update_fields = [
            'status',
            'shipped_at',
            'delivered_at',
            'tracking_number',
            'updated_at',
        ]
        shipment.save(update_fields=update_fields)

        logger.info(
            'shipment_status_changed',
            extra={
                'shipment_id': shipment.pk,
                'internal_tracking': shipment.internal_tracking,
                'old_status': current_status,
                'new_status': new_status,
            },
        )

        # ── Интеграция с Order: синхронизируем статус заказа ──
        ShippingService._sync_order_status(shipment, new_status)

        return shipment

    # ==============================================================
    # ИНТЕГРАЦИЯ С ЗАКАЗАМИ
    # ==============================================================

    @staticmethod
    def _sync_order_status(shipment: Shipment, shipment_status: str) -> None:
        """
        Синхронизирует статус заказа с статусом отправления.

        ПРАВИЛА:
          • IN_TRANSIT → Order.PROCESSING (заказ в обработке)
          • DELIVERED  → Order.DELIVERED (заказ доставлен)
          • RETURNED   → Order.CANCELLED (заказ отменён)

        Оборачиваем в try/except — ошибка синхронизации статуса заказа
        не должна откатывать транзакцию отправления.
        """
        from apps.orders.models import Order
        from apps.orders.services.order_service import OrderService

        order_status_map = {
            'in_transit': OrderStatus.PROCESSING,
            'delivered': OrderStatus.DELIVERED,
            'returned': OrderStatus.CANCELLED,
        }

        target_order_status = order_status_map.get(shipment_status)
        if not target_order_status:
            return

        try:
            order = Order.objects.get(pk=shipment.order_id)
            if order.status != target_order_status:
                OrderService.transition_status(
                    order, target_order_status,
                )
                logger.info(
                    'order_status_synced_from_shipment',
                    extra={
                        'order_id': order.pk,
                        'order_number': order.order_number,
                        'shipment_status': shipment_status,
                        'new_order_status': target_order_status,
                    },
                )
        except Exception as exc:
            logger.error(
                'order_status_sync_error',
                extra={
                    'order_id': shipment.order_id,
                    'shipment_status': shipment_status,
                    'error': str(exc),
                },
            )

    # ==============================================================
    # ОПРЕДЕЛЕНИЕ ЗОНЫ
    # ==============================================================

    @staticmethod
    def _resolve_zone(
        zone_code: str | None = None,
        region: str | None = None,
    ) -> ShippingZone | None:
        """
        Определяет зону доставки по коду или названию региона.

        АЛГОРИТМ:
          1. Если передан zone_code → ищем по коду
          2. Если передан region → ищем зону, содержащую этот регион
          3. Если ничего не передано → None

        RETURNS:
            ShippingZone или None
        """
        if zone_code:
            try:
                return ShippingZone.objects.get(
                    zone_code=zone_code,
                    is_active=True,
                )
            except ShippingZone.DoesNotExist:
                return None

        if region:
            # Перебираем все активные зоны и ищем ту, которая содержит регион.
            # Для production стоит использовать PostgreSQL JSONB queries
            # для поиска по JSON-полю без перебора в Python.
            for zone in ShippingZone.objects.filter(is_active=True):
                if zone.contains_region(region):
                    return zone

        return None

    # ==============================================================
    # ПОЛУЧЕНИЕ ОТПРАВЛЕНИЯ
    # ==============================================================

    @staticmethod
    def get_shipment_by_order(order) -> Shipment:
        """
        Возвращает отправление для заказа.

        RAISES:
            NotFound: если отправление не найдено
        """
        try:
            return Shipment.objects.select_related(
                'order', 'method', 'method__zone',
            ).get(order=order)
        except Shipment.DoesNotExist:
            raise NotFound(
                f'Отправление для заказа {order.order_number} не найдено.'
            )

    @staticmethod
    def get_shipment_by_tracking(tracking_number: str) -> Shipment:
        """
        Возвращает отправление по трек-номеру (внешнему или внутреннему).

        RAISES:
            NotFound: если отправление не найдено
        """
        try:
            return Shipment.objects.select_related(
                'order', 'method', 'method__zone', 'user',
            ).get(
                models.Q(tracking_number=tracking_number)
                | models.Q(internal_tracking=tracking_number)
            )
        except Shipment.DoesNotExist:
            raise NotFound(
                f'Отправление с трек-номером «{tracking_number}» не найдено.'
            )
