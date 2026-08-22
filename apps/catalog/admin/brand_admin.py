# ────────────────────────────────────────────────────────────
# BrandAdmin — админка для управления брендами.
#
# ФУНКЦИОНАЛ:
#   - Список брендов с логотипом, именем, slug, активностью
#   - Превью логотипа прямо в списке (40×40px)
#   - Счётчик товаров для каждого бренда
#   - Фильтр по is_active
#   - Поиск по имени и slug
#   - Slug автогенерируется из name
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В Django Admin (/admin/catalog/brand/) — пусто.
#   Бренды нельзя будет создать/редактировать через админку.
# ────────────────────────────────────────────────────────────

# admin — модуль Django для настройки административного интерфейса.
from django.contrib import admin

# format_html — экранирует HTML и помечает строку как безопасную
# для рендеринга в Django Admin (предотвращает XSS).
# Без format_html: HTML-теги отобразятся как текст (<img ...>).
from django.utils.html import format_html

# Brand — модель бренда (name, slug, logo, description, is_active).
from apps.catalog.models import Brand


# @admin.register(Brand) — регистрирует BrandAdmin для модели Brand.
# Эквивалентно: admin.site.register(Brand, BrandAdmin)
# Но @admin.register удобнее — нельзя забыть зарегистрировать.
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    # list_display — колонки в списке брендов (/admin/catalog/brand/).
    # Порядок = порядок колонок в таблице.
    list_display = (
        'id',               # PK — для быстрой идентификации
        'logo_preview',     # Кастомная колонка — превью логотипа (метод ниже)
        'name',             # Название бренда
        'slug',             # URL-идентификатор
        'is_active',        # Флаг активности (boolean)
        'products_count',   # Кастомная колонка — количество товаров
        'created_at',       # Дата создания (для сортировки)
    )

    # list_filter — боковая панель фильтров.
    # Только is_active — фильтр «Активные / Неактивные».
    list_filter = ('is_active',)

    # search_fields — поля для полнотекстового поиска.
    # name — по названию бренда ('Apple')
    # slug — по URL-идентификатору ('apple')
    search_fields = ('name', 'slug')

    # readonly_fields — поля, которые нельзя редактировать.
    # created_at / updated_at — авто-поля (auto_now_add / auto_now)
    # slug НЕ в readonly — он должен быть в форме для prepopulated_fields
    readonly_fields = ('created_at', 'updated_at')

    # prepopulated_fields — автогенерация slug из name.
    # При вводе «Apple» → slug автоматически «apple».
    # Работает через JavaScript в Django Admin.
    # ВНИМАНИЕ: slug НЕ должен быть в readonly_fields одновременно!
    prepopulated_fields = {'slug': ('name',)}

    # list_per_page — количество записей на странице.
    # 50 — оптимальный баланс: не слишком длинный список,
    # но и не слишком частая пагинация.
    list_per_page = 50

    def get_queryset(self, request):
        """
        Оптимизация: prefetch products для products_count.

        ПОЧЕМУ PREFETCH_RELATED, А НЕ select_related:
            products — reverse FK (OneToMany: у бренда много товаров).
            select_related не работает с reverse FK.
            prefetch_related — один дополнительный запрос:
            SELECT * FROM catalog_product WHERE brand_id IN (...)
        """
        return (
            super()
            .get_queryset(request)
            .prefetch_related('products')
        )

    @admin.display(description='Логотип')
    # description='Логотип' — заголовок колонки в списке.
    def logo_preview(self, obj):
        """
        HTML-превью логотипа в списке брендов.

        obj — экземпляр Brand.
        format_html — экранирует URL и помечает строку как безопасную.
        Без format_html: <img src="..."> отобразится как текст.
        """
        if obj.logo:
            # obj.logo.url — URL файла логотипа (из ImageField).
            # width/height=40 — компактный размер для списка.
            # object-fit:contain — логотип не обрезается.
            # border-radius:4px — скруглённые углы.
            return format_html(
                '<img src="{}" width="40" height="40" '
                'style="object-fit:contain; border-radius:4px;" />',
                obj.logo.url,
            )
        # Если логотип не загружен — показываем тире.
        return '—'

    @admin.display(description='Товаров')
    def products_count(self, obj):
        """
        Количество товаров бренда.

        obj.products.count() — использует prefetch_related
        из get_queryset() → не создаёт дополнительный SQL.
        Без prefetch: products.count() = N дополнительных запросов.
        """
        return obj.products.count()
