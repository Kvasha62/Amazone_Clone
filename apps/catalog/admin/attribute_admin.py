# ────────────────────────────────────────────────────────────
# AttributeAdmin + AttributeValueAdmin — админка для EAV-атрибутов.
#
# EAV = Entity-Attribute-Value:
#   Attribute — название характеристики («Цвет», «Размер»)
#   AttributeValue — возможное значение («Красный», «XL»)
#   VariantAttribute — связка вариант↔значение (в отдельном файле)
#
# ФУНКЦИОНАЛ:
#   - Attribute с inline-значениями (TabularInline)
#   - Счётчик значений для каждого атрибута
#   - AttributeValue с фильтром по атрибуту и цветным превью
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/attribute/ и /admin/catalog/attributevalue/ — пусто.
#   Нельзя управлять характеристиками товаров.
# ────────────────────────────────────────────────────────────

# admin — модуль Django для настройки административного интерфейса.
from django.contrib import admin

# Модели EAV: Attribute (характеристика) и AttributeValue (значение).
from apps.catalog.models import Attribute, AttributeValue


# ────────────────────────────────────────────────────────────
# Inline для значений атрибута (внутри страницы атрибута)
# ────────────────────────────────────────────────────────────

# TabularInline — значения отображаются в таблице внутри страницы Attribute.
# Альтернатива: StackedInline — вертикальные блоки (занимает больше места).
# TabularInline компактнее — для коротких значений (value + color_hex) оптимально.
class AttributeValueInline(admin.TabularInline):
    # model — модель для inline (AttributeValue).
    # Без: Django не знает какую модель отображать.
    model = AttributeValue
    # extra=1 — сколько пустых строк для добавления показывать.
    # extra=1 — одна пустая строка (можно добавить значение).
    # extra=0 — не показывать пустые строки (только «Добавить» кнопку).
    extra = 1
    # fields — какие поля показывать в таблице.
    fields = ('value', 'color_hex')
    # ordering — сортировка значений по алфавиту.
    ordering = ('value',)


# ────────────────────────────────────────────────────────────
# AttributeAdmin — управление характеристиками
# ────────────────────────────────────────────────────────────

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    # list_display — колонки списка атрибутов.
    list_display = (
        'id',               # PK
        'name',             # Название: «Цвет», «Размер»
        'slug',             # URL-slug: 'color', 'size'
        'values_count',     # Кастомная колонка — количество значений
    )

    # search_fields — поиск по названию атрибута.
    search_fields = ('name',)

    # readonly_fields — slug автогенерируется, даты — авто.
    readonly_fields = ('slug', 'created_at', 'updated_at')

    # inlines — встраиваемые модели.
    # AttributeValueInline — значения атрибута прямо на странице атрибута.
    # Без: пришлось бы идти на отдельную страницу /attributevalue/
    # для каждого значения — неудобно.
    inlines = (AttributeValueInline,)

    def get_queryset(self, request):
        """
        Оптимизация: prefetch values для values_count.
        values — related_name для AttributeValue.attribute.
        """
        return (
            super()
            .get_queryset(request)
            .prefetch_related('values')
        )

    @admin.display(description='Значений')
    def values_count(self, obj):
        """
        Количество значений атрибута.
        Использует prefetch из get_queryset() → без дополнительного SQL.
        """
        return obj.values.count()


# ────────────────────────────────────────────────────────────
# AttributeValueAdmin — управление значениями атрибутов
# ────────────────────────────────────────────────────────────

@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    # list_display — колонки списка значений.
    list_display = (
        'id',               # PK
        'attribute',        # Родительский атрибут: «Цвет»
        'value',            # Значение: «Красный»
        'color_hex',        # HEX-код цвета: '#FF0000'
    )

    # list_filter — фильтр по атрибуту (все значения «Цвета» / «Размеры»).
    list_filter = ('attribute',)

    # search_fields — поиск по значению и по названию атрибута.
    # attribute__name — навигация по FK (Django double-underscore).
    search_fields = ('value', 'attribute__name')

    # list_select_related — JOIN к attribute в одном запросе.
    # Без: каждый attribute_id → отдельный SQL для отображения имени.
    # select_related='attribute' → один запрос вместо N+1.
    list_select_related = ('attribute',)

    # Цветной превью в колонке color_hex.
    # Метод определён, но НЕ добавлен в list_display выше!
    # TODO: добавить 'color_preview' в list_display если нужен визуальный превью.
    @admin.display(description='Цвет')
    def color_preview(self, obj):
        """
        Цветной квадрат-превью для значений типа «цвет».

        ПОЧЕМУ format_html:
            Генерируем <span style="background:#FF0000">...</span>.
            Без format_html: HTML отобразится как текст.
        """
        if obj.color_hex:
            # Lazy-импорт — format_html нужна только если есть цвет.
            from django.utils.html import format_html
            return format_html(
                '<span style="display:inline-block; width:24px; height:24px; '
                'background:{}; border-radius:4px; border:1px solid #ccc;"></span>',
                obj.color_hex,
            )
        return '—'
