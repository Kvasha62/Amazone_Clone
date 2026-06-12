# ────────────────────────────────────────────────────────────────────────
# apps/shipping/admin/shipping_admin.py — админка для моделей доставки.
#
# Регистрирует ShippingZone, ShippingMethod, Shipment в Django Admin.
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# ────────────────────────────────────────────────────────────────────────

from django.contrib import admin

from apps.shipping.models import Shipment, ShippingMethod, ShippingZone


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    """Админка для зон доставки."""

    list_display = ('id', 'name', 'zone_code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'zone_code')
    ordering = ('name',)
    list_per_page = 50


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    """Админка для способов доставки."""

    list_display = (
        'id', 'name', 'shipping_type', 'zone',
        'base_price', 'price_per_kg',
        'free_shipping_threshold', 'is_active',
        'estimated_days_min', 'estimated_days_max',
    )
    list_filter = ('shipping_type', 'is_active', 'zone')
    search_fields = ('name',)
    raw_id_fields = ('zone',)
    list_per_page = 50
    ordering = ('sort_order', 'base_price')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    """Админка для отправлений."""

    list_display = (
        'id', 'internal_tracking', 'tracking_number',
        'order', 'status', 'shipping_cost',
        'shipped_at', 'delivered_at',
    )
    list_filter = ('status', 'method__shipping_type')
    search_fields = (
        'internal_tracking', 'tracking_number',
        'order__order_number',
    )
    raw_id_fields = ('order', 'user', 'method')
    list_per_page = 50
    ordering = ('-created_at',)
    readonly_fields = ('internal_tracking', '_tracking_seq')
