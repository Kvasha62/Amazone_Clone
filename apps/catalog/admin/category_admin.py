from django.contrib import admin

from apps.catalog.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'name',
        'parent',
        'path',
        'is_active',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
        'slug',
    )

    ordering = (
        'path',
    )

    readonly_fields = (
        'path',
        'created_at',
        'updated_at',
    )