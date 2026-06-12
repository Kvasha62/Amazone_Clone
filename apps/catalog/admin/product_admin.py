# ────────────────────────────────────────────────────────────
# ProductAdmin — админка для управления товарами.
#
# ФУНКЦИОНАЛ:
#   - Список товаров с цветным статусом, ценами, рейтингом
#   - Inline-изображения и варианты (TabularInline)
#   - Fieldsets для группировки полей
#   - Цветной статус (emoji + CSS-цвет)
#   - Диапазон цен (из денормализованных min_price/max_price)
#
# АРХИТЕКТУРА:
#   ProductImageInline — редактирование изображений внутри товара
#   ProductVariantInline — редактирование вариантов внутри товара
#   show_change_link — ссылка на полную страницу варианта
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/product/ — пусто. Товары нельзя создавать/редактировать.
# ────────────────────────────────────────────────────────────

# admin — модуль Django для настройки админки.
from django.contrib import admin

# format_html — безопасный рендеринг HTML в admin.
from django.utils.html import format_html

# ProductStatus — Enum статусов товара (ACTIVE, DRAFT, OUT_OF_STOCK, ARCHIVED).
from apps.catalog.constants import ProductStatus

# Модели для admin и inline.
from apps.catalog.models import (
    Product,
    ProductImage,
    ProductVariant,
)


# ────────────────────────────────────────────────────────────
# ProductImageInline — изображения внутри страницы товара
# ────────────────────────────────────────────────────────────

# TabularInline — компактная таблица изображений.
class ProductImageInline(admin.TabularInline):
    # model — модель изображений.
    model = ProductImage
    # extra=0 — не показывать пустые строки для добавления.
    # Изображения загружаются через отдельный интерфейс (drag-and-drop),
    # не через inline-таблицу.
    extra = 0
    # fields — колонки в inline-таблице.
    fields = ('image_preview', 'image', 'alt', 'is_main', 'order')
    # readonly_fields — image_preview вычисляется (не в БД).
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        """
        Превью изображения в inline-таблице (80×80px).

        obj — экземпляр ProductImage.
        obj.image — ImageField (URL файла).
        """
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" '
                'style="object-fit:cover; border-radius:4px;" />',
                obj.image.url,
            )
        return '—'
    # short_description — заголовок колонки.
    # Без: заголовок = 'Image preview' (из имени метода).
    image_preview.short_description = 'Превью'


# ────────────────────────────────────────────────────────────
# ProductVariantInline — варианты внутри страницы товара
# ────────────────────────────────────────────────────────────

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    # extra=0 — варианты создаются через отдельный процесс (импорт/сервис).
    extra = 0
    # fields — минимум полей для inline-таблицы.
    fields = ('sku', 'barcode', 'is_active', 'weight')
    # show_change_link=True — ссылка «Изменить» на полную страницу варианта.
    # Без: для редактирования атрибутов варианта пришлось бы искать его
    # в общем списке /admin/catalog/productvariant/.
    show_change_link = True


# ────────────────────────────────────────────────────────────
# ProductAdmin — основная конфигурация товара в admin
# ────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # list_display — колонки списка товаров.
    list_display = (
        'id',                   # PK
        'name',                 # Название товара
        'brand',                # Бренд (FK, отображается __str__)
        'primary_category',     # Главная категория (FK)
        'status_colored',       # Кастомная — цветной статус с emoji
        'price_range',          # Кастомная — «1 000 – 5 000 ₽»
        'rating',               # Средний рейтинг
        'is_featured',          # Рекомендуемый (boolean)
        'created_at',           # Дата создания
    )

    # list_filter — боковые фильтры.
    list_filter = (
        'status',               # По статусу: Active, Draft, ...
        'is_featured',          # Рекомендуемые / Обычные
        'brand',                # По бренду
        'primary_category',     # По категории
    )

    # search_fields — полнотекстовый поиск.
    # brand__name — поиск по имени бренда (FK navigation).
    # uuid — поиск по публичному идентификатору.
    search_fields = (
        'name',
        'description',
        'manufacturer_code',
        'brand__name',
        'uuid',
    )

    # list_select_related — JOIN к brand и category в списке.
    # Без: каждый product.brand → отдельный SQL (N+1).
    # select_related = один JOIN вместо N запросов.
    list_select_related = (
        'brand',
        'primary_category',
    )

    # readonly_fields — поля только для чтения.
    # uuid — генерируется автоматически.
    # status — меняется через сервис (не напрямую).
    # created_at/updated_at — авто-поля.
    # published_at — устанавливается сервисом при публикации.
    readonly_fields = (
        'uuid',
        'status',
        'created_at',
        'updated_at',
        'published_at',
    )

    # ordering — сортировка по умолчанию (новые первыми).
    ordering = ('-created_at',)

    # inlines — встраиваемые модели внутри страницы товара.
    inlines = (
        ProductImageInline,     # Изображения товара
        ProductVariantInline,   # Варианты товара
    )

    # fieldsets — группировка полей на странице редактирования.
    fieldsets = (
        # Основная информация — ядро товара.
        ('Основная информация', {
            'fields': (
                'name',         # Название (обязательное)
                'slug',         # URL-slug (readonly)
                'description',  # Полное описание (textarea)
            ),
        }),
        # Каталог — связи с другими сущностями.
        ('Каталог', {
            'fields': (
                'brand',                # FK к бренду
                'primary_category',     # Главная категория (FK)
                'categories',           # M2M категории (все привязки)
                'tags',                 # M2M теги
                'manufacturer_code',    # Артикул производителя
            ),
        }),
        # Статус — управление публикацией.
        ('Статус', {
            'fields': (
                'status',       # ACTIVE/DRAFT/OUT_OF_STOCK/ARCHIVED
                'is_featured',  # Рекомендуемый товар
                'published_at', # Дата публикации (readonly)
            ),
        }),
        # Цены — денормализованные (автоматически из вариантов).
        ('Цены (авто)', {
            'description': 'Пересчитываются автоматически из вариантов.',
            'fields': (
                'min_price',    # Минимальная цена
                'max_price',    # Максимальная цена
            ),
        }),
        # Рейтинг — агрегированные данные.
        ('Рейтинг', {
            'fields': (
                'rating',           # Средний рейтинг (float)
                'reviews_count',    # Количество отзывов
                'views_count',      # Количество просмотров
            ),
        }),
        # SEO — мета-теги для поисковых систем.
        ('SEO', {
            'fields': (
                'meta_title',       # <title>
                'meta_description', # <meta name="description">
            ),
        }),
        # Системные — свёрнутая секция с техническими полями.
        ('Системные', {
            'classes': ('collapse',),   # Свёрнута по умолчанию
            'fields': (
                'uuid',         # Публичный UUID
                'created_at',   # Дата создания
                'updated_at',   # Дата обновления
            ),
        }),
    )

    # ----------------------------------------------------------
    # Custom columns
    # ----------------------------------------------------------

    @admin.display(description='Статус', ordering='status')
    # ordering='status' — позволяет сортировать колонку по полю status.
    def status_colored(self, obj):
        """
        Цветной статус с emoji для быстрой визуальной идентификации.

        ПОЧЕМУ НЕ ПРОСТО ТЕКСТ:
            В списке из 50 товаров глаз быстрее находит цвет+emoji,
            чем текст «Активный» / «Черновик».
            ✅ = активный, 📝 = черновик, ⚠️ = нет в наличии, 📦 = архив.

        ПОЧЕМУ format_html:
            Чтобы задать цвет текста через inline style.
            Без: <span style="color:red"> отобразится как текст.
        """
        colors = {
            # ACTIVE — зелёный (успех, всё ок)
            ProductStatus.ACTIVE: ('#16a34a', '✅'),
            # DRAFT — серый (в процессе, не опубликован)
            ProductStatus.DRAFT: ('#9ca3af', '📝'),
            # OUT_OF_STOCK — оранжевый (внимание, нужно пополнить)
            ProductStatus.OUT_OF_STOCK: ('#ea580c', '⚠️'),
            # ARCHIVED — серый (удалён из каталога)
            ProductStatus.ARCHIVED: ('#6b7280', '📦'),
        }
        # colors.get() с fallback — защита от неизвестного статуса.
        # Если status=None или не из enum → серый + ❓.
        color, icon = colors.get(obj.status, ('#999', '❓'))
        return format_html(
            '<span style="color:{}; font-weight:600;">{} {}</span>',
            color,
            icon,
            # get_status_display() — Django-метод для choices:
            # 'active' → 'Активный' (из ProductStatus.choices).
            obj.get_status_display(),
        )

    @admin.display(description='Цена', ordering='min_price')
    # ordering='min_price' — сортировка по минимальной цене.
    def price_range(self, obj):
        """
        Диапазон цен товара.

        obj.price_range — property на модели Product:
        возвращает строку вида «1 000 – 5 000 ₽» или «1 000 ₽».
        """
        return obj.price_range
