from django.contrib import admin

from apps.catalog.models import (
    Product,
    ProductImage,
    ProductVariant
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0

    fields = (
        'sku',
        'barcode',
        'is_active',
    )

    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'name',
        'brand',
        'category',
        'rating',
        'reviews_count',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
        'brand',
        'category',
    )

    search_fields = (
        'name',
        'description',
        'manufacturer_code',
        'brand__name',
    )

    list_select_related = (
        'brand',
        'category',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    ordering = (
        '-created_at',
    )

    inlines = (
        ProductImageInline,
        ProductVariantInline,
    )

    fieldsets = (

        (
            'Основная информация',
            {
                'fields': (
                    'name',
                    'slug',
                    'description',
                )
            }
        ),

        (
            'Каталог',
            {
                'fields': (
                    'brand',
                    'category',
                    'manufacturer_code',
                )
            }
        ),

        (
            'Рейтинг',
            {
                'fields': (
                    'rating',
                    'reviews_count',
                )
            }
        ),

        (
            'SEO',
            {
                'fields': (
                    'meta_title',
                    'meta_description',
                )
            }
        ),

        (
            'Служебные поля',
            {
                'fields': (
                    'is_active',
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )