from django.contrib import admin

from apps.cart.models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ('variant',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'session_key_hash_short',
        'is_active',
        'items_count',
        'created_at',
    )
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__email', 'session_key_hash')
    autocomplete_fields = ('user',)
    readonly_fields = ('session_key_hash', 'created_at', 'updated_at')
    inlines = (CartItemInline,)

    def get_queryset(self, request):
        # Снимаем N+1: подтягиваем юзера + prefetch items для count
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('items')

    @admin.display(description='Сессия')
    def session_key_hash_short(self, obj: Cart):
        if not obj.session_key_hash:
            return '—'
        return f'{obj.session_key_hash[:12]}…'

    @admin.display(description='Позиций')
    def items_count(self, obj: Cart):
        # prefetched в get_queryset — без N+1
        return len(obj.items.all()) if hasattr(obj, '_prefetched_objects_cache') else obj.items.count()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cart',
        'variant',
        'quantity',
        'created_at',
    )
    list_select_related = ('cart', 'variant')
    autocomplete_fields = ('cart', 'variant')
    search_fields = ('variant__sku', 'cart__user__username')
    readonly_fields = ('created_at', 'updated_at')
