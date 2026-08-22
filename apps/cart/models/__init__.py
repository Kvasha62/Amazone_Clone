# ────────────────────────────────────────────────────────────────────────
# apps/cart/models/__init__.py — реэкспорт моделей корзины.
#
# АРХИТЕКТУРНАЯ РОЛЬ:
#   Позволяет импортировать модели из одного места:
#     from apps.cart.models import Cart, CartItem
#   Вместо:
#     from apps.cart.models.cart import Cart
#     from apps.cart.models.cart_item import CartItem
#
# Django автоматически обнаруживает models/ пакет и загружает все модели.
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
#
# __all__ — белый список для from apps.cart.models import *
# Без __all__: import * вытащит BaseModel, models, и прочий мусор.
# 📖 https://docs.python.org/3/tutorial/modules.html#importing-from-a-package
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   from apps.cart.models import Cart → ImportError
#   Все файлы, импортирующие модели корзины, перестанут работать.
# ────────────────────────────────────────────────────────────────────────

# Импортируем каждую модель из своего файла.
# Почему отдельные файлы, а не один models.py:
#   Cart ~140 строк + CartItem ~105 строк = 245 строк.
#   Это не критично, но при росте (добавление CartCoupon, CartShipping и т.д.)
#   единый models.py превратится в 1000+ строк — нечитаемо.
from apps.cart.models.cart import Cart
from apps.cart.models.cart_item import CartItem

# __all__ — перечислены модели, доступные через import *.
# Алфавитный порядок для удобства.
__all__ = ['Cart', 'CartItem']
