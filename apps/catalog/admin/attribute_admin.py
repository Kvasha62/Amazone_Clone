from django.contrib import admin

from apps.catalog.models import (
    Attribute,
    AttributeValue
)


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):

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


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'attribute',
        'value',
        'created_at',
    )

    list_filter = (
        'attribute',
    )

    search_fields = (
        'value',
        'attribute__name',
    )

    ordering = (
        'attribute',
        'value',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )