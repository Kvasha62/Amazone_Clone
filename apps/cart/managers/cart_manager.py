# ────────────────────────────────────────────────────────────────────────
# apps/cart/managers/cart_manager.py — менеджер модели Cart.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП:
#   Django разделяет Manager (точка входа: Cart.objects) и
#   QuerySet (методы цепочки: .active().with_items()).
#
#   Manager.from_queryset(CartQuerySet) «встраивает» все методы
#   QuerySet в Manager. Результат:
#     Cart.objects.active()     ← из CartQuerySet.active()
#     Cart.objects.full()       ← из CartQuerySet.full()
#     Cart.objects.with_items() ← из CartQuerySet.with_items()
#
#   Без from_queryset: пришлось бы писать прокси-методы вручную:
#     class CartManager(models.Manager):
#         def active(self): return self.get_queryset().active()
#         def full(self):   return self.get_queryset().full()
#     ... и при добавлении метода в QuerySet — добавлять прокси.
#   from_queryset делает это АВТОМАТИЧЕСКИ.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#from-queryset
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#creating-a-manager-with-queryset-methods
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Cart.objects.active() → AttributeError
#   • Cart.objects.full() → AttributeError
#   • Cart.objects.with_items() → AttributeError
#   • Все API-эндпоинты корзины перестанут работать
# ────────────────────────────────────────────────────────────────────────

# models — ORM Django (Manager, QuerySet и т.д.)
from django.db import models

# CartQuerySet — класс с методами цепочки (active, for_user, with_items, full).
# 📖 см. apps/cart/querysets/cart_queryset.py
from apps.cart.querysets.cart_queryset import CartQuerySet


# Manager.from_queryset(CartQuerySet) — фабричный метод Django.
# Возвращает НОВЫЙ класс Manager, который содержит все методы CartQuerySet.
#
# КАК ЭТО РАБОТАЕТ (под капотом):
#   Django динамически создаёт класс:
#     class CartManager(models.Manager):
#         def active(self, *args, **kwargs):
#             return self.get_queryset().active(*args, **kwargs)
#         def full(self, *args, **kwargs):
#             return self.get_queryset().full(*args, **kwargs)
#         ...
#   Каждый метод QuerySet становится прокси-методом Manager.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
class CartManager(models.Manager.from_queryset(CartQuerySet)):
    """
    Менеджер корзины.

    Все QuerySet-методы (active / with_items / full / …)
    доступны напрямую через Cart.objects благодаря from_queryset.

    Прокси-методы убраны — from_queryset(CartQuerySet) уже делает
    их доступными как Cart.objects.active(), Cart.objects.full() и т.д.
    """
    # pass — класс-контейнер, вся магия в from_queryset().
    # Можно добавить кастомные методы менеджера (не QuerySet) здесь:
    # например, get_by_session() или get_stats().
    pass
