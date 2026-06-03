from django.contrib import admin

from apps.catalog.models import (
    ProductVariant,
    VariantAttribute
)


class VariantAttributeInline(
    admin.TabularInline
):
    model = VariantAttribute

    extra = 0


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'product',
        'sku',
        'barcode',
        'is_active',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'sku',
        'barcode',
        'product__name',
    )

    list_select_related = (
        'product',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    inlines = (
        VariantAttributeInline,
    )