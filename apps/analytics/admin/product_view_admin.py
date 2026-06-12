# ────────────────────────────────────────────────────────────────────────
# apps/analytics/admin/product_view_admin.py — админка для просмотров.
# ────────────────────────────────────────────────────────────────────────

from django.contrib import admin
from apps.analytics.models import ProductView


@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    """Админка для просмотров товаров."""

    list_display = (
        'id', 'product', 'user', 'source',
        'ip_address', 'created_at',
    )
    list_filter = ('source', 'created_at')
    search_fields = ('product__name', 'user__email', 'session_key')
    raw_id_fields = ('product', 'user')
    readonly_fields = (
        'product', 'user', 'session_key', 'source',
        'ip_address', 'user_agent', 'created_at', 'updated_at',
    )
    list_per_page = 100
    ordering = ('-created_at',)
