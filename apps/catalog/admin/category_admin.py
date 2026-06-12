# ────────────────────────────────────────────────────────────
# CategoryAdmin — админка для управления категориями (дерево).
#
# ОСОБЕННОСТИ:
#   - Категории используют treebeard MP_Node (Materialized Path)
#   - fieldsets для группировки полей (Основная инфо, SEO, Система)
#   - Системные поля treebeard скрыты в collapse-секцию
#   - Массовые действия: активировать / деактивировать
#   - Превью URL-пути в списке
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/category/ — пусто.
#   Категории нельзя будет создать/редактировать.
# ────────────────────────────────────────────────────────────

# admin — модуль Django для настройки админки.
from django.contrib import admin

# format_html — безопасный рендеринг HTML в Django Admin.
from django.utils.html import format_html

# Category — модель категории (treebeard MP_Node).
from apps.catalog.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # list_display — колонки списка категорий.
    list_display = (
        'name',             # Название: «Электроника»
        'slug',             # URL-slug: 'elektronika'
        'depth',            # Глубина в дереве (1=корень)
        'numchild',         # Количество детей (подкатегорий)
        'is_active',        # Активна ли категория
        'products_count',   # Кастомная колонка — количество товаров
        'url_path',         # Кастомная колонка — URL-путь (денормализованный)
    )

    # list_filter — боковые фильтры.
    # is_active — активные / неактивные.
    # depth — по уровню вложенности (1, 2, 3...).
    list_filter = ('is_active', 'depth')

    # search_fields — поиск по названию и slug.
    search_fields = ('name', 'slug')

    # readonly_fields — поля только для чтения.
    # slug — автогенерируется (не редактируется вручную).
    # depth, numchild, path — поля treebeard (управляются автоматически).
    # url_path, full_name_cached — денормализованные поля (вычисляются).
    # created_at, updated_at — авто-поля.
    readonly_fields = (
        'slug',
        'depth',
        'numchild',
        'url_path',
        'full_name_cached',
        'path',
        'created_at',
        'updated_at',
    )

    # fieldsets — группировка полей на странице редактирования.
    # Каждый кортеж = (заголовок_секции, {options}).
    fieldsets = (
        # Секция «Основная информация» — главные поля категории.
        ('Основная информация', {
            'fields': (
                'name',         # Название категории
                'slug',         # URL-slug (readonly)
                'description',  # Описание (текст)
                'image',        # Изображение категории
            ),
        }),
        # Секция «SEO» — мета-теги для поисковых систем.
        ('SEO', {
            'fields': (
                'meta_title',       # <title> страницы
                'meta_description', # <meta name="description">
            ),
        }),
        # Секция «Статус» — активность категории.
        ('Статус', {
            'fields': ('is_active',),
        }),
        # Секция «Системные (treebeard)» — технические поля.
        # classes=('collapse',) — секция свёрнута по умолчанию.
        # description — подсказка для администратора.
        ('Системные (treebeard)', {
            'classes': ('collapse',),
            'description': (
                'Управление деревом — через методы treebeard. '
                'Не редактировать вручную.'
            ),
            'fields': (
                'depth',            # Глубина в дереве
                'numchild',         # Количество детей
                'path',             # Materialized Path (например '00010002')
                'url_path',         # URL-путь: /catalog/elektronika/
                'full_name_cached', # «Электроника > Смартфоны > Apple»
                'created_at',       # Дата создания
                'updated_at',       # Дата обновления
            ),
        }),
    )

    # ----------------------------------------------------------
    # Действия (actions) — массовые операции через чекбоксы.
    # ----------------------------------------------------------

    @admin.action(description='Деактивировать выбранные категории')
    def deactivate(self, request, queryset):
        """
        Массовая деактивация категорий.

        queryset — выбранные через чекбоксы категории.
        .update(is_active=False) — один SQL:
        UPDATE catalog_category SET is_active = False WHERE id IN (...)

        Без: пришлось бы кликать каждую категорию → убрать is_active → сохранить.
        """
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано: {updated}')

    @admin.action(description='Активировать выбранные категории')
    def activate(self, request, queryset):
        """Массовая активация категорий."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано: {updated}')

    # actions — регистрация действий в выпадающем списке.
    actions = ('deactivate', 'activate')

    # ----------------------------------------------------------
    # Custom columns
    # ----------------------------------------------------------

    def get_queryset(self, request):
        """
        Оптимизация: prefetch products для products_count.
        """
        return (
            super()
            .get_queryset(request)
            .prefetch_related('products')
        )

    @admin.display(description='Товаров', ordering='numchild')
    # ordering='numchild' — позволяет сортировать колонку по количеству детей.
    # (Не идеально — numchild != products_count, но приближённо.)
    def products_count(self, obj):
        """
        Количество товаров в категории.

        Использует prefetch_related из get_queryset().
        """
        return obj.products.count()

    @admin.display(description='URL', ordering='url_path')
    # ordering='url_path' — сортировка по URL-пути.
    def url_path(self, obj):
        """
        Отображение URL-пути в списке категорий.

        ПОЧЕМУ format_html, А НЕ ПРОСТО obj.url_path:
            Чтобы задать моноширинный шрифт для URL —
            удобнее читать /catalog/elektronika/smartfony/.
        """
        if not obj.url_path:
            return '—'
        # font-family:monospace — равная ширина символов для URL.
        # font-size:12px — компактный размер для списка.
        return format_html(
            '<span style="font-family:monospace; font-size:12px;">{}</span>',
            obj.url_path,
        )
