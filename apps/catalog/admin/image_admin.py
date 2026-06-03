from django.contrib import admin

from apps.catalog.models import ProductImage


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'product',
        'is_main',
        'order',
    )

    list_filter = (
        'is_main',
    )

    search_fields = (
        'product__name',
    )

    ordering = (
        'product',
        'order',
    )