# ────────────────────────────────────────────────────────────────────────
# apps/orders/serializers/__init__.py — реэкспорт сериализаторов заказа.
#
# Центральная точка импорта для views и других модулей:
#   from apps.orders.serializers import OrderSerializer, CreateOrderInputSerializer
#
# 📖 https://www.django-rest-framework.org/api-guide/serializers/
# ────────────────────────────────────────────────────────────────────────

from apps.orders.serializers.order_serializers import (
    CreateOrderInputSerializer,
    OrderItemSerializer,
    OrderListSerializer,
    OrderSerializer,
    OrderStatusTransitionSerializer,
    CancelOrderInputSerializer,
)

__all__ = [
    'CreateOrderInputSerializer',
    'OrderItemSerializer',
    'OrderListSerializer',
    'OrderSerializer',
    'OrderStatusTransitionSerializer',
    'CancelOrderInputSerializer',
]
