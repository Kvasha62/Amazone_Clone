# ────────────────────────────────────────────────────────────────────────
# apps/pricing/admin/price_admin.py — Django Admin для цен и истории.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# ────────────────────────────────────────────────────────────────────────

from django.contrib import admin

from apps.pricing.models import Price, PriceHistory


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    """
    Admin для актуальных цен вариантов.
    Показывает: вариант, цена, скидка, эффективная цена, % скидки.
    """
    list_display = (
        'id', 'variant', 'price', 'sale_price',
        'effective_price_display', 'discount_percent_display',
        'currency', 'updated_at',
    )
    list_filter = ('currency',)
    # Двойной select_related: variant → product — без N+1.
    list_select_related = ('variant', 'variant__product')
    search_fields = ('variant__sku', 'variant__product__name')
    readonly_fields = ('created_at', 'updated_at')
    # raw_id_fields — текстовое поле для variant (тысячи записей).
    raw_id_fields = ('variant',)

    @admin.display(description='Эффект. цена')
    def effective_price_display(self, obj):
        """Показывает эффективную цену (sale или base)."""
        return f'{obj.effective_price:.2f}'

    @admin.display(description='Скидка %')
    def discount_percent_display(self, obj):
        """Показывает % скидки или —."""
        pct = obj.discount_percent
        return f'{pct}%' if pct is not None else '—'


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """
    Admin для истории изменений цен (read-only аудит).
    """
    list_display = (
        'id', 'variant', 'old_price', 'new_price',
        'old_sale_price', 'new_sale_price',
        'changed_by', 'created_at',
    )
    list_select_related = ('variant', 'changed_by')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('variant__sku',)
    raw_id_fields = ('variant', 'changed_by')
