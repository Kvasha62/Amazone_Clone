# ────────────────────────────────────────────────────────────────────────
# apps/inventory/admin/stock_admin.py — Django Admin для склада.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# ────────────────────────────────────────────────────────────────────────

from django.contrib import admin

from apps.inventory.models import Stock, StockMovement


class StockMovementInline(admin.TabularInline):
    """Inline для движений внутри Stock."""
    model = StockMovement
    extra = 0
    readonly_fields = (
        'kind', 'delta', 'quantity_before', 'quantity_after',
        'order', 'performed_by', 'note', 'created_at',
    )
    can_delete = False
    max_num = 0
    fields = (
        'kind', 'delta', 'quantity_before', 'quantity_after',
        'note', 'created_at',
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Admin для Stock — остатки на складе."""

    list_display = (
        'variant_sku', 'quantity', 'reserved_quantity',
        'available_display', 'is_low_stock', 'updated_at',
    )
    list_filter = ('quantity',)
    search_fields = ('variant__sku', 'variant__product__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_per_page = 50
    inlines = (StockMovementInline,)

    @admin.display(description='SKU', ordering='variant__sku')
    def variant_sku(self, obj):
        return getattr(obj.variant, 'sku', '—')

    @admin.display(description='Доступно')
    def available_display(self, obj):
        return obj.available_quantity


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Admin для StockMovement — аудит всех движений."""

    list_display = (
        'stock_variant', 'kind', 'delta',
        'quantity_before', 'quantity_after',
        'order_number', 'created_at',
    )
    list_filter = ('kind',)
    search_fields = ('stock__variant__sku', 'note')
    readonly_fields = (
        'stock', 'kind', 'delta', 'quantity_before', 'quantity_after',
        'order', 'performed_by', 'note', 'created_at',
    )
    ordering = ('-created_at',)
    list_per_page = 50

    @admin.display(description='Вариант')
    def stock_variant(self, obj):
        return str(obj.stock)

    @admin.display(description='Заказ')
    def order_number(self, obj):
        return getattr(obj.order, 'order_number', '—')
