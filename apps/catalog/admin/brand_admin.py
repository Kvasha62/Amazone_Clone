from django.contrib import admin

from apps.catalog.models import Brand


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'name',
        'slug',
        'created_at',
    )

    search_fields = (
        'name',
        'slug',
    )

    ordering = (
        'name',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )