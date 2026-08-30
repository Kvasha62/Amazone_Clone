# ────────────────────────────────────────────────────────────
# ProductAdmin — админка для управления товарами.
#
# ФУНКЦИОНАЛ:
#   - Список товаров с цветным статусом, ценами, рейтингом
#   - Inline-изображения и варианты (TabularInline)
#   - Fieldsets для группировки полей
#   - Цветной статус (emoji + CSS-цвет)
#   - Диапазон цен (из денормализованных min_price/max_price) — только чтение
#   - filter_horizontal для M2M (категории, теги) — добавление/удаление
#
# АРХИТЕКТУРА:
#   ProductImageInline — редактирование изображений внутри товара
#   ProductVariantInline — редактирование вариантов внутри товара
#   show_change_link — ссылка на полную страницу варианта
#
# ARCH-001 Stage 2 (M1 residual — Product bounds):
#   Product.min_price / max_price — денормализованные границы цен.
#   Единственный авторитетный путь их обновления:
#
#     PricingService.recalculate_product_bounds(product)
#       → CatalogService.set_product_prices(product, min_price, max_price)
#
#   catalog НЕ импортирует pricing (запрещена обратная зависимость),
#   поэтому Admin не может пересчитать границы сам — он их только
#   показывает (readonly_fields) и ЗАПРЕЩАЕТ любую запись отличных
#   значений (defense-in-depth в save_model).
#
# ARCH-001 H2 (review aggregates):
#   Product.rating / reviews_count — денормализованные агрегаты отзывов.
#   ProductAdmin показывает их как readonly и запрещает forced save;
#   пересчёт остаётся за ReviewService → CatalogService.set_review_stats().
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/product/ — пусто. Товары нельзя создавать/редактировать.
# ────────────────────────────────────────────────────────────

from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Product,
    ProductImage,
    ProductVariant,
)

# ARCH-001 Stage 2 (M1 residual): денормализованные границы цен товара.
# Писать их имеет право только CatalogService.set_product_prices()
# (вызывается из PricingService) — Admin только читает.
PRODUCT_PRICE_BOUNDS_FIELDS = ('min_price', 'max_price')

# ARCH-001 H2: review-derived aggregate fields. CatalogService.set_review_stats()
# is the catalog-owned service-level write path; ProductAdmin may display these
# values but must not persist arbitrary Admin-supplied values.
PRODUCT_REVIEW_AGGREGATE_FIELDS = ('rating', 'reviews_count')

PRODUCT_ADMIN_PROTECTED_FIELDS = (
    *PRODUCT_PRICE_BOUNDS_FIELDS,
    *PRODUCT_REVIEW_AGGREGATE_FIELDS,
)
PRODUCT_REVIEW_AGGREGATE_DEFAULTS = {
    'rating': Decimal('0.00'),
    'reviews_count': 0,
}


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
    """Inline variants on Product change form.

    ARCH-001 Stage 2: ``is_active`` is read-only and existing rows cannot be
    deleted here. Price-relevant mutations go through
    ``PricingService.set_variant_active`` / ``delete_variant`` only.
    New variants may still be added (creation does not stale bounds by itself;
    bounds update when prices are set via PricingService).
    """

    model = ProductVariant
    extra = 0
    fields = ('sku', 'barcode', 'is_active', 'weight')
    readonly_fields = ('is_active',)
    show_change_link = True
    # Disables the per-row delete checkbox for existing variants.
    can_delete = False


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
        # ARCH-001 Stage 2 (M1): границы цен — только чтение.
        # Источник истины — PricingService → CatalogService.set_product_prices.
        'min_price',
        'max_price',
        # ARCH-001 H2: review-derived aggregates — только чтение.
        # Источник истины: ReviewService → CatalogService.set_review_stats.
        'rating',
        'reviews_count',
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
            'description': (
                'Только чтение. Пересчитываются PricingService → '
                'CatalogService.set_product_prices(). '
                'Ручное изменение через Admin запрещено (ARCH-001 Stage 2).'
            ),
            'fields': (
                'min_price',
                'max_price',
            ),
        }),
        ('Рейтинг / отзывы', {
            'description': (
                'rating и reviews_count — только чтение: рассчитываются '
                'ReviewService по одобренным отзывам и записываются через '
                'CatalogService.set_review_stats() (ARCH-001 H2). '
                'views_count не относится к review-агрегатам H2.'
            ),
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
    # ARCH-001 Stage 2 / H2: защита денормализованных агрегатов
    # ----------------------------------------------------------

    def save_model(self, request, obj, form, change):
        """Refuse persisting protected aggregate fields from ProductAdmin.

        ``readonly_fields`` removes the protected fields from generated
        ModelForms, so a normal Admin POST cannot bind them. This override is
        the second layer: a crafted POST, a direct ``save_model()`` call, or a
        future edit of ``readonly_fields`` still cannot persist arbitrary
        aggregate values.

        Legitimate service-level paths stay outside Admin orchestration:
        ``PricingService`` → ``CatalogService.set_product_prices()`` for price
        bounds and ``ReviewService`` → ``CatalogService.set_review_stats()``
        for review aggregates. ProductAdmin forbids the mutations instead of
        importing pricing/reviews services.
        """
        if change and obj.pk:
            previous = (
                Product.objects.filter(pk=obj.pk)
                .values(*PRODUCT_ADMIN_PROTECTED_FIELDS)
                .first()
            )
            if previous is not None:
                changed_fields = [
                    field
                    for field in PRODUCT_ADMIN_PROTECTED_FIELDS
                    if getattr(obj, field) != previous[field]
                ]
                if changed_fields:
                    raise PermissionDenied(
                        'Изменение защищённых Product aggregate fields через '
                        f'Admin запрещено (ARCH-001): {changed_fields}. '
                        'Используйте соответствующие service-level пути.'
                    )
        elif (
            obj.min_price is not None
            or obj.max_price is not None
            or any(
                getattr(obj, field) != default
                for field, default in PRODUCT_REVIEW_AGGREGATE_DEFAULTS.items()
            )
        ):
            # Add path: a new Product must start with empty derived values.
            raise PermissionDenied(
                'Задание Product aggregate fields через Admin запрещено '
                '(ARCH-001). Денормализованные значения публикуются через '
                'соответствующие service-level пути.'
            )

        super().save_model(request, obj, form, change)

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
