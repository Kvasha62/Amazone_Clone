# ────────────────────────────────────────────────────────────────────────
# apps/orders/api_views/__init__.py — реэкспорт view-классов заказов.
#
# Центральная точка импорта для urls.py:
#   from apps.orders.api_views import OrderListView, OrderDetailView, ...
# ────────────────────────────────────────────────────────────────────────

from apps.orders.api_views.order_views import (
    OrderCancelView,
    OrderDetailView,
    OrderListView,
    OrderStatusView,
)

__all__ = [
    'OrderCancelView',
    'OrderDetailView',
    'OrderListView',
    'OrderStatusView',
]
