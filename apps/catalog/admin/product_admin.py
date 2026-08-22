# ────────────────────────────────────────────────────────────
# ProductAdmin — админка для управления товарами.
#
# ФУНКЦИОНАЛ:
#   - Список товаров с цветным статусом, ценами, рейтингом
#   - Inline-изображения и варианты (TabularInline)
#   - Fieldsets для группировки полей
#   - Цветной статус (emoji + CSS-цвет)
#   - Диапазон цен (из денормализованных min_price/max_price)
#   - filter_horizontal для M2M (категории, теги) — добавление/удаление
#
# АРХИТЕКТУРА:
#   ProductImageInline — редактирование изображений внутри товара
#   ProductVariantInline — редактирование вариантов внутри товара
#   show_change_link — ссылка на полную страницу варианта
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/product/ — пусто. Товары нельзя создавать/редактировать.
# ────────────────────────────────────────────────────────────

from django.contrib import admin
from django.utils.html import format_html

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Product,
    ProductImage,
    ProductVariant,
)


# ────────────────────────────────────────────────────────────
# ProductImageInline
# ────────────────────────────────────────────────────────────

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ('image_preview', 'image', 'alt', 'is_main', 'order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" '
                'style="object-fit:cover; border-radius:4px;" />',
                obj.image.url,
            )
        return '—'
    image_preview.short_description = 'Превью'


# ────────────────────────────────────────────────────────────
# ProductVariantInline
# ────────────────────────────────────────────────────────────

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'barcode', 'is_active', 'weight')
    show_change_link = True


# ────────────────────────────────────────────────────────────
# ProductAdmin
# ────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'brand',
        'primary_category',
        'status_colored',
        'price_range',
        'rating',
        'is_featured',
        'created_at',
    )

    list_filter = (
        'status',
        'is_featured',
        'brand',
        'primary_category',
    )

    search_fields = (
        'name',
        'description',
        'manufacturer_code',
        'brand__name',
        'uuid',
    )

    list_select_related = (
        'brand',
        'primary_category',
    )

    # ══════════════════════════════════════════════════════════
    # filter_horizontal — ДВУХПАНЕЛЬНЫЙ ВИДЖЕТ ДЛЯ M2M
    # ══════════════════════════════════════════════════════════
    # БЕЗ filter_horizontal:
    #   Django рисует <select multiple> — можно добавить (Ctrl+Click),
    #   но УДАЛИТЬ НЕЛЬЗЯ — нет кнопки «Убрать».
    #
    # С filter_horizontal:
    #   Две панели: «Доступные» ← → «Выбранные»
    #   Кнопки: «Добавить» и «Удалить»
    #   Можно и добавлять, и удалять.
    # ══════════════════════════════════════════════════════════
    filter_horizontal = ('categories', 'tags')

    readonly_fields = (
        'uuid',
        'created_at',
        'updated_at',
        'published_at',
    )

    ordering = ('-created_at',)

    inlines = (
        ProductImageInline,
        ProductVariantInline,
    )

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'name',
                'slug',
                'description',
            ),
        }),
        ('Каталог', {
            'fields': (
                'brand',
                'primary_category',
                'categories',
                'tags',
                'manufacturer_code',
            ),
        }),
        ('Статус', {
            'fields': (
                'status',
                'is_featured',
                'published_at',
            ),
        }),
        ('Цены (авто)', {
            'description': 'Пересчитываются автоматически из вариантов.',
            'fields': (
                'min_price',
                'max_price',
            ),
        }),
        ('Рейтинг', {
            'fields': (
                'rating',
                'reviews_count',
                'views_count',
            ),
        }),
        ('SEO', {
            'fields': (
                'meta_title',
                'meta_description',
            ),
        }),
        ('Системные', {
            'classes': ('collapse',),
            'fields': (
                'uuid',
                'created_at',
                'updated_at',
            ),
        }),
    )

    # ----------------------------------------------------------
    # Custom columns
    # ----------------------------------------------------------

    @admin.display(description='Статус', ordering='status')
    def status_colored(self, obj):
        colors = {
            ProductStatus.ACTIVE: ('#16a34a', '✅'),
            ProductStatus.DRAFT: ('#9ca3af', '📝'),
            ProductStatus.OUT_OF_STOCK: ('#ea580c', '⚠️'),
            ProductStatus.ARCHIVED: ('#6b7280', '📦'),
        }
        color, icon = colors.get(obj.status, ('#999', '❓'))
        return format_html(
            '<span style="color:{}; font-weight:600;">{} {}</span>',
            color,
            icon,
            obj.get_status_display(),
        )

    @admin.display(description='Цена', ordering='min_price')
    def price_range(self, obj):
        return obj.price_range
