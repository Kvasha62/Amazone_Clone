# ────────────────────────────────────────────────────────────────────────
# apps/users/admin/address_admin.py — Django Admin для адресов доставки.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# ────────────────────────────────────────────────────────────────────────

from django.contrib import admin

from apps.users.models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin для адресов доставки — просмотр, поиск, фильтрация."""

    list_display = (
        'id', 'user', 'recipient_name', 'city',
        'street', 'is_default', 'created_at',
    )
    list_filter = ('is_default', 'country')
    # list_select_related — JOIN к user (без N+1 при отображении).
    list_select_related = ('user',)
    search_fields = (
        'recipient_name', 'user__email', 'user__username',
        'city', 'street', 'postal_code',
    )
    # raw_id_fields — текстовое поле с ID (оптимально при млн пользователей).
    # autocomplete_fields может быть медленным для огромных таблиц.
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
