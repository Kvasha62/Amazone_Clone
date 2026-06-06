from django.contrib import admin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from apps.catalog.models import Category


@admin.register(Category)
class CategoryAdmin(TreeAdmin):
    form = movenodeform_factory(Category)

    list_display = (
        'id',
        'name',
        'depth',           # вместо parent
        'url_path',        # вместо старого path
        'is_active',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    readonly_fields = (
        'url_path',
        'full_name_cached',
        'created_at',
        'updated_at',
    )
    # ordering НЕ задаём — TreeAdmin сортирует по системному path