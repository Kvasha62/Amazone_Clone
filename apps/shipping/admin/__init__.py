# ────────────────────────────────────────────────────────────────────────
# apps/shipping/admin/__init__.py — реэкспорт админ-классов.
# ────────────────────────────────────────────────────────────────────────

from apps.shipping.admin.shipping_admin import (
    ShippingMethodAdmin,
    ShippingZoneAdmin,
    ShipmentAdmin,
)

__all__ = ['ShippingZoneAdmin', 'ShippingMethodAdmin', 'ShipmentAdmin']
