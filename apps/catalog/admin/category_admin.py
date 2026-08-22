# ────────────────────────────────────────────────────────────
# CategoryAdmin — админка для управления категориями (дерево).
#
# ИСПОЛЬЗУЕТ treebeard TreeAdmin + MoveNodeForm:
#   - Древовидный список с drag-and-drop
#   - Поля «Позиция» и «Родитель» в форме создания/редактирования
#   - Автоматический вызов add_root() / add_child() при сохранении
#
# ВАЖНО:
#   - НЕ используем fieldsets — MoveNodeForm добавляет свои поля
#     (treebeard_position, treebeard_ref_node), и при fieldsets
#     они не появятся на форме.
#   - НЕ используем prefetch_related — конфликтует с .iterator()
#     при удалении (treebeard bug).
#   - НЕ указываем list_display — TreeAdmin показывает дерево
#     с отступами и drag-and-drop вместо обычной таблицы.
# ────────────────────────────────────────────────────────────

from django.contrib import admin
from django.db.models import Count

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from apps.catalog.models import Category


@admin.register(Category)
class CategoryAdmin(TreeAdmin):
    # ══════════════════════════════════════════════════════════
    # ФОРМА — MoveNodeForm
    # ══════════════════════════════════════════════════════════
    # movenodeform_factory(Category) создаёт форму на основе
    # MoveNodeForm, которая добавляет:
    #   treebeard_position — First child of / Before / After
    #   treebeard_ref_node — выбор родителя (-- root -- = корень)
    #
    # При сохранении форма САМА вызывает add_root()/add_child().
    # ══════════════════════════════════════════════════════════
    form = movenodeform_factory(Category)

    # ══════════════════════════════════════════════════════════
    # СПИСОК КАТЕГОРИЙ
    # ══════════════════════════════════════════════════════════
    # НЕ указываем list_display — TreeAdmin использует шаблон
    # tree_change_list.html с отступами и drag-and-drop.
    # Если указать list_display — будет обычная таблица без дерева.
    # ══════════════════════════════════════════════════════════
    list_display = ('name', 'slug', 'depth', 'is_active')
    list_filter = ('is_active', 'depth')
    search_fields = ('name', 'slug')

    # ══════════════════════════════════════════════════════════
    # READONLY FIELDS
    # ══════════════════════════════════════════════════════════
    # НЕ включаем depth, numchild, path — они управляются
    # treebeard и добавляются в форму автоматически.
    # readonly_fields только для наших кастомных полей.
    # ══════════════════════════════════════════════════════════
    readonly_fields = (
        'slug',
        'url_path',
        'full_name_cached',
        'created_at',
        'updated_at',
    )

    # ══════════════════════════════════════════════════════════
    # ПОЛЯ ФОРМЫ (вместо fieldsets)
    # ══════════════════════════════════════════════════════════
    # НЕ используем fieldsets — он прячет поля treebeard_position
    # и treebeard_ref_node, которые MoveNodeForm добавляет к форме.
    # fields = (...) показывает ВСЕ поля включая treebeard-поля.
    # ══════════════════════════════════════════════════════════
    fields = (
        'treebeard_position',
        'treebeard_ref_node',
        'name',
        'slug',
        'description',
        'image',
        'is_active',
        'meta_title',
        'meta_description',
        'url_path',
        'full_name_cached',
        'created_at',
        'updated_at',
    )

    # ══════════════════════════════════════════════════════════
    # ДЕЙСТВИЯ
    # ══════════════════════════════════════════════════════════

    @admin.action(description='Деактивировать выбранные категории')
    def deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано: {updated}')

    @admin.action(description='Активировать выбранные категории')
    def activate(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано: {updated}')

    actions = ('deactivate', 'activate')

    # ══════════════════════════════════════════════════════════
    # QUERYSET — annotate вместо prefetch_related
    # ══════════════════════════════════════════════════════════

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_products_count=Count('products'))
        )
