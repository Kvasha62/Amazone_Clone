# ────────────────────────────────────────────────────────────
# TagAdmin — админка для управления тегами.
#
# ФУНКЦИОНАЛ:
#   - Список тегов с id, name, slug, активностью, количеством товаров
#   - Inline-редактирование is_active (прямо в списке!)
#   - Фильтр по is_active
#   - Поиск по имени
#   - Slug автогенерируется (readonly)
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/tag/ — пусто. Теги нельзя будет создавать/редактировать.
# ────────────────────────────────────────────────────────────

# admin — модуль Django для настройки админки.
from django.contrib import admin

# Tag — модель тега (name, slug, is_active).
from apps.catalog.models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    # list_display — колонки в списке тегов.
    list_display = (
        'id',               # PK
        'name',             # Название тега: «Новинка»
        'slug',             # URL-slug: 'novinka'
        'is_active',        # Флаг активности
        'products_count',   # Кастомная колонка — сколько товаров с этим тегом
    )

    # list_filter — фильтр по активности.
    list_filter = ('is_active',)

    # search_fields — поиск по названию тега.
    search_fields = ('name',)

    # readonly_fields — slug только для чтения (генерируется автоматически).
    # created_at/updated_at — авто-поля.
    readonly_fields = ('slug', 'created_at', 'updated_at')

    # list_editable — поля, которые можно редактировать ПРЯМО В СПИСКЕ.
    # is_active — чекбокс прямо в таблице (без перехода на страницу редактирования).
    # Без: кликнуть тег → снять галочку → сохранить = 3 клика вместо 1.
    # ВАЖНО: поле должно быть в list_display! И не первым (первая колонка = ссылка на редактирование).
    list_editable = ('is_active',)

    # list_per_page — записей на страницу.
    # 100 — тегов может быть много, длинный список приемлем.
    list_per_page = 100

    def get_queryset(self, request):
        """
        Оптимизация: prefetch products для products_count.
        """
        return (
            super()
            .get_queryset(request)
            .prefetch_related('products')
        )

    @admin.display(description='Товаров')
    def products_count(self, obj):
        """
        Количество товаров с этим тегом.
        Использует prefetch из get_queryset().
        """
        return obj.products.count()
