# ────────────────────────────────────────────────────────────────────────
# apps/cart/serializers/__init__.py — реэкспорт сериализаторов корзины.
#
# Фасад-паттерн: единая точка импорта для views.
#   from apps.cart.serializers import CartSerializer
# Вместо:
#   from apps.cart.serializers.cart_serializers import CartSerializer
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   from apps.cart.serializers import CartSerializer → ImportError
# ────────────────────────────────────────────────────────────────────────

from apps.cart.serializers.cart_serializers import (
    AddToCartInputSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateCartItemInputSerializer,
)

__all__ = [
    'AddToCartInputSerializer',
    'CartItemSerializer',
    'CartSerializer',
    'UpdateCartItemInputSerializer',
]
