# ────────────────────────────────────────────────────────────────────────
# apps/shipping/api_views/__init__.py — реэкспорт API views.
# ────────────────────────────────────────────────────────────────────────

from apps.shipping.api_views.shipping_views import (
    ShipmentCreateView,
    ShipmentDetailView,
    ShipmentListView,
    ShipmentStatusView,
    ShipmentTrackingByCodeView,
    ShipmentTrackingView,
    ShippingCostView,
    ShippingMethodListView,
)

__all__ = [
    'ShipmentCreateView',
    'ShipmentDetailView',
    'ShipmentListView',
    'ShipmentStatusView',
    'ShipmentTrackingByCodeView',
    'ShipmentTrackingView',
    'ShippingCostView',
    'ShippingMethodListView',
]
