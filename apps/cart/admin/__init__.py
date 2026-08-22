# ────────────────────────────────────────────────────────────────────────
# apps/cart/admin/__init__.py — реэкспорт admin-классов корзины.
#
# При импорте срабатывает побочный эффект: @admin.register(Cart) и
# @admin.register(CartItem) регистрируют модели в Django Admin.
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#modeladmin-objects
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   /admin/cart/ — пусто, модели Cart и CartItem не появятся в админке.
# ────────────────────────────────────────────────────────────────────────

from apps.cart.admin.cart_admin import (
    CartAdmin,
    CartItemAdmin,
    CartItemInline,
)

__all__ = ['CartAdmin', 'CartItemAdmin', 'CartItemInline']
