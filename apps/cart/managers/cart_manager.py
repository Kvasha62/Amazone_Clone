from django.db import models

from apps.cart.querysets.cart_queryset import CartQuerySet


class CartManager(models.Manager.from_queryset(CartQuerySet)):
    """
    Менеджер корзины.

    Все QuerySet-методы (active / with_items / full / …)
    доступны напрямую через Cart.objects благодаря from_queryset.

    Прокси-методы убраны — from_queryset(CartQuerySet) уже делает
    их доступными как Cart.objects.active(), Cart.objects.full() и т.д.
    """
    pass

