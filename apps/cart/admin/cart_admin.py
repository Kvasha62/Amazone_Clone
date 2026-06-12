# ────────────────────────────────────────────────────────────────────────
# apps/cart/admin/cart_admin.py — Django Admin для корзин.
#
# ДВА ADMIN-КЛАССА + ОДИН INLINE:
#   CartItemInline  — позиции внутри страницы корзины (TabularInline)
#   CartAdmin       — управление корзинами (/admin/cart/cart/)
#   CartItemAdmin   — управление позициями (/admin/cart/cartitem/)
#
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#inlinemodeladmin-objects
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   /admin/cart/ — пусто, нет возможности управлять корзинами.
# ────────────────────────────────────────────────────────────────────────

# admin — модуль Django для административного интерфейса.
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#module-django.contrib.admin
from django.contrib import admin

# Cart, CartItem — модели корзины.
from apps.cart.models import Cart, CartItem


# ────────────────────────────────────────────────────────────────────────
# CartItemInline — позиции внутри страницы корзины
# ────────────────────────────────────────────────────────────────────────

# TabularInline — компактная таблица для редактирования связанных объектов.
# Показывается внутри страницы CartAdmin.
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#tabularinline
class CartItemInline(admin.TabularInline):
    """Inline-редактирование позиций корзины."""
    # model — связанная модель для inline.
    model = CartItem
    # extra=0 — не показывать пустые строки для добавления.
    # Позиции добавляются через API, не через admin.
    extra = 0
    # autocomplete_fields — Select2 autocomplete для variant
    # (вариантов может быть тысячи — dropdown непрактичен).
    # 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    autocomplete_fields = ('variant',)
    # readonly_fields — системные поля (не редактируются).
    readonly_fields = ('created_at', 'updated_at')
    # fields — отображаемые колонки в inline-таблице.
    fields = ('variant', 'quantity', 'created_at', 'updated_at')


# ────────────────────────────────────────────────────────────────────────
# CartAdmin — управление корзинами
# ────────────────────────────────────────────────────────────────────────

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin для корзин. Показывает:
      - пользователя / хэш сессии
      - активность
      - количество позиций
      - даты создания/обновления
    """
    # list_display — колонки в списке корзин.
    list_display = (
        'id',                       # PK
        'user',                     # Пользователь (FK, __str__)
        'session_key_hash_short',   # Кастомная — укороченный хэш
        'is_active',                # Активна (boolean)
        'items_count',              # Кастомная — количество позиций
        'created_at',               # Дата создания
        'updated_at',               # Дата обновления
    )
    # list_filter — фильтр по активности.
    list_filter = ('is_active',)
    # search_fields — поиск по username, email, хэшу.
    search_fields = ('user__username', 'user__email', 'session_key_hash')
    # autocomplete_fields — Select2 для user (тысячи пользователей).
    autocomplete_fields = ('user',)
    # readonly_fields — session_key_hash не редактируется (хэш).
    readonly_fields = ('session_key_hash', 'created_at', 'updated_at')
    # inlines — встраиваемые позиции внутри корзины.
    inlines = (CartItemInline,)
    # actions — массовые действия.
    actions = ('deactivate_selected',)

    def get_queryset(self, request):
        """
        Оптимизация: select_related(user) + prefetch_related(items).
        Без: N+1 запросов при отображении списка корзин.
        """
        qs = super().get_queryset(request)
        # select_related('user') — INNER JOIN к auth_user.
        # prefetch_related('items') — для items_count.
        return qs.select_related('user').prefetch_related('items')

    @admin.display(description='Сессия')
    def session_key_hash_short(self, obj: Cart):
        """
        Укороченный хэш сессии (первые 12 символов).
        Полный хэш = 64 символа — слишком длинный для колонки.
        """
        if not obj.session_key_hash:
            return '—'
        return f'{obj.session_key_hash[:12]}…'

    @admin.display(description='Позиций')
    def items_count(self, obj: Cart):
        """
        Количество позиций в корзине.

        hasattr(obj, '_prefetched_objects_cache') — проверяем
        был ли prefetch_related. Если да → items.all() из кэша (0 SQL).
        Если нет → items.count() — 1 SQL (оптимальнее .all()).
        """
        return len(obj.items.all()) if hasattr(obj, '_prefetched_objects_cache') else obj.items.count()

    @admin.action(description='Деактивировать выбранные корзины')
    def deactivate_selected(self, request, queryset):
        """
        Массовая деактивация корзин.
        .update(is_active=False) — один SQL:
        UPDATE cart_cart SET is_active = False WHERE id IN (...)
        """
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {updated} корзин.')


# ────────────────────────────────────────────────────────────────────────
# CartItemAdmin — управление позициями корзин (отдельная страница)
# ────────────────────────────────────────────────────────────────────────

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Admin для позиций корзин. Полезно для аналитики и отладки:
    какие товары добавляют, сколько штук, когда.
    """
    list_display = (
        'id',       # PK
        'cart',     # Корзина (FK)
        'variant',  # Вариант товара (FK)
        'quantity', # Количество
        'created_at', # Дата добавления
    )
    # list_filter — фильтр по активности корзины.
    list_filter = ('cart__is_active',)
    # list_select_related — JOIN к cart и variant в списке.
    list_select_related = ('cart', 'variant')
    # autocomplete_fields — Select2 для cart и variant.
    autocomplete_fields = ('cart', 'variant')
    # search_fields — поиск по SKU варианта и username.
    search_fields = ('variant__sku', 'cart__user__username')
    # readonly_fields — системные поля.
    readonly_fields = ('created_at', 'updated_at')
    # raw_id_fields — текстовое поле с ID (для миллионов записей).
    # autocomplete_fields может быть медленным при огромных таблицах.
    raw_id_fields = ('cart', 'variant')
