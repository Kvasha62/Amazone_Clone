# ────────────────────────────────────────────────────────────────────────
# apps/shipping/tests/factories.py — тестовые фабрики для модуля доставки.
#
# Хелпер-функции для создания тестовых данных.
# Используются во всех тестах shipping-модуля.
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.utils import timezone

from apps.shipping.constants import (
    SHIPPING_TYPE_COURIER,
    SHIPPING_TYPE_PICKUP,
    SHIPPING_TYPE_POST,
)


def create_test_zone(
    *,
    name: str = 'Москва и МО',
    zone_code: str = 'msk',
    regions: list | None = None,
    is_active: bool = True,
):
    """Создаёт тестовую зону доставки."""
    from apps.shipping.models import ShippingZone

    if regions is None:
        regions = ['Москва', 'Московская область']

    return ShippingZone.objects.create(
        name=name,
        zone_code=zone_code,
        regions=regions,
        is_active=is_active,
    )


def create_test_method(
    zone=None,
    *,
    name: str = 'Курьерская доставка',
    shipping_type: str = SHIPPING_TYPE_COURIER,
    base_price: Decimal = Decimal('300.00'),
    price_per_kg: Decimal = Decimal('50.000'),
    free_shipping_threshold: Decimal | None = Decimal('5000.00'),
    max_shipping_cost: Decimal | None = None,
    estimated_days_min: int = 1,
    estimated_days_max: int = 3,
    max_weight_kg: Decimal = Decimal('30.000'),
    is_active: bool = True,
    sort_order: int = 10,
    pickup_address: str = '',
):
    """Создаёт тестовый способ доставки."""
    from apps.shipping.models import ShippingMethod

    if zone is None:
        zone = create_test_zone()

    return ShippingMethod.objects.create(
        name=name,
        shipping_type=shipping_type,
        zone=zone,
        base_price=base_price,
        price_per_kg=price_per_kg,
        free_shipping_threshold=free_shipping_threshold,
        max_shipping_cost=max_shipping_cost,
        estimated_days_min=estimated_days_min,
        estimated_days_max=estimated_days_max,
        max_weight_kg=max_weight_kg,
        is_active=is_active,
        sort_order=sort_order,
        pickup_address=pickup_address,
    )


def create_test_shipment(
    order,
    method=None,
    *,
    user=None,
    shipping_cost: Decimal = Decimal('300.00'),
    weight_kg: Decimal | None = None,
    status: str = 'preparing',
    tracking_number: str = '',
    notes: str = '',
):
    """Создаёт тестовое отправление."""
    from apps.shipping.models import Shipment

    if method is None:
        method = create_test_method()

    if user is None:
        user = order.user

    return Shipment.objects.create(
        order=order,
        user=user,
        method=method,
        status=status,
        shipping_cost=shipping_cost,
        weight_kg=weight_kg,
        tracking_number=tracking_number,
        notes=notes,
    )
