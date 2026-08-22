# ────────────────────────────────────────────────────────────
# ProductVariantAdmin — админка для управления вариантами товаров.
#
# ФУНКЦИОНАЛ:
#   - Список вариантов с SKU, штрих-кодом, товаром, активностью
#   - Inline для атрибутов варианта (VariantAttribute)
#   - Поиск по SKU, штрих-коду, названию товара
#   - select_related для товара (без N+1)
#   - Autocomplete для атрибутов и значений
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   В /admin/catalog/productvariant/ — пусто.
#   Варианты можно редактировать только через inline на странице товара
#   (но там ограниченный набор полей).
# ────────────────────────────────────────────────────────────

# admin — модуль Django для настройки админки.
from django.contrib import admin

# Модели: ProductVariant (вариант) и VariantAttribute (EAV-связка).
from apps.catalog.models import ProductVariant, VariantAttribute


# ────────────────────────────────────────────────────────────
# VariantAttributeInline — атрибуты варианта внутри страницы варианта
# ────────────────────────────────────────────────────────────

# TabularInline — компактная таблица атрибутов.
class VariantAttributeInline(admin.TabularInline):
    # VariantAttribute — модель EAV-связки:
    # variant + attribute + value = «iPhone 15 Pro / Цвет / Красный»
    model = VariantAttribute
    # extra=1 — одна пустая строка для добавления нового атрибута.
    extra = 1
    # fields — какие поля показывать в inline-таблице.
    fields = ('attribute', 'value')
    # autocomplete_fields — Django заменяет dropdown на autocomplete-виджет.
    # Без: если атрибутов 100+ — dropdown будет огромным и медленным.
    # Autocomplete — поиск с подсказками через Select2.
    autocomplete_fields = ('attribute', 'value')


# ────────────────────────────────────────────────────────────
# ProductVariantAdmin — основная конфигурация
# ────────────────────────────────────────────────────────────

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    # list_display — колонки списка вариантов.
    list_display = (
        'id',               # PK
        'sku',              # Артикул: «IP15P-128-BLK»
        'barcode',          # Штрих-код: «4902430566785»
        'product',          # Товар-родитель (FK, __str__)
        'is_active',        # Активен ли вариант
        'weight',           # Вес (для доставки)
        'created_at',       # Дата создания
    )

    # list_filter — фильтр по активности.
    list_filter = ('is_active',)

    # search_fields — поиск по ключевым полям.
    # product__name — поиск по названию родительского товара.
    search_fields = ('sku', 'barcode', 'product__name')

    # list_select_related — JOIN к product в одном запросе.
    # Без: каждый variant.product → отдельный SQL (N+1).
    list_select_related = ('product',)

    # readonly_fields — slug и даты не редактируются вручную.
    readonly_fields = ('slug', 'created_at', 'updated_at')

    # inlines — встраиваемые атрибуты варианта.
    inlines = (VariantAttributeInline,)

    # list_per_page — записей на страницу.
    # Вариантов может быть много (10+ на товар × 1000 товаров = 10000).
    list_per_page = 50
