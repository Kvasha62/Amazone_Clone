# ────────────────────────────────────────────────────────────
# ProductVariantAdmin — админка для управления вариантами товаров.
#
# ФУНКЦИОНАЛ:
#   - Список вариантов с SKU, штрих-кодом, товаром, активностью
#   - Inline для атрибутов варианта (VariantAttribute)
#   - Поиск по SKU, штрих-коду, названию товара
#   - select_related для товара (без N+1)
#   - Autocomplete для атрибутов и значений
#
# ARCH-001 Stage 2 (price bounds):
#   `is_active` and deletion are price-relevant. The only legitimate
#   mutation path is PricingService.set_variant_active /
#   PricingService.delete_variant (pricing → CatalogService).
#   catalog Admin MUST NOT import PricingService (no catalog → pricing).
#   Therefore Admin forbids those mutations; safe fields remain editable.
#   See ARCHITECTURE.md → Cross-Domain Coordination / Price Bounds.
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/productvariant/ — пусто.
#   Варианты можно редактировать только через inline на странице товара
#   (но там ограниченный набор полей).
# ────────────────────────────────────────────────────────────

from django.contrib import admin
from django.core.exceptions import PermissionDenied

from apps.catalog.models import ProductVariant, VariantAttribute


class VariantAttributeInline(admin.TabularInline):
    model = VariantAttribute
    extra = 1
    fields = ('attribute', 'value')
    autocomplete_fields = ('attribute', 'value')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'sku',
        'barcode',
        'product',
        'is_active',
        'weight',
        'created_at',
    )

    list_filter = ('is_active',)

    search_fields = ('sku', 'barcode', 'product__name')

    list_select_related = ('product',)

    # ARCH-001 Stage 2: is_active is price-relevant — read-only in Admin.
    # Changing it requires PricingService.set_variant_active() (not callable
    # from catalog without reverse dependency).
    readonly_fields = ('slug', 'is_active', 'created_at', 'updated_at')

    inlines = (VariantAttributeInline,)

    list_per_page = 50

    # ── ARCH-001 Stage 2: block delete paths ──────────────────────────
    # Single-object delete, bulk action delete, and any permission-gated
    # UI entry that would call ModelAdmin.delete_model / delete_queryset
    # without PricingService.delete_variant().

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        raise PermissionDenied(
            'Удаление ProductVariant через Admin запрещено (ARCH-001 Stage 2). '
            'Используйте PricingService.delete_variant().'
        )

    def delete_queryset(self, request, queryset):
        raise PermissionDenied(
            'Массовое удаление ProductVariant через Admin запрещено '
            '(ARCH-001 Stage 2). Используйте PricingService.delete_variant().'
        )

    def save_model(self, request, obj, form, change):
        """Refuse persisting a changed is_active even if form was forced."""
        if change and obj.pk:
            previous = ProductVariant.objects.filter(pk=obj.pk).values_list(
                'is_active', flat=True,
            ).first()
            if previous is not None and obj.is_active != previous:
                raise PermissionDenied(
                    'Изменение ProductVariant.is_active через Admin запрещено '
                    '(ARCH-001 Stage 2). Используйте '
                    'PricingService.set_variant_active().'
                )
        super().save_model(request, obj, form, change)
