# ==============================================================================
# apps/catalog/managers/product_manager.py — Менеджер товара
# ==============================================================================
# ProductManager = базовый Manager + все методы ProductQuerySet.
#
# from_queryset() — Django-магия:
#   Берёт методы из QuerySet (active, visible, catalog, for_card, ...)
#   и «приклеивает» их к менеджеру.
#
# Результат:
#   Product.objects.active()          — работает
#   Product.objects.visible()         — работает
#   Product.objects.catalog()         — работает
#   Product.objects.for_card()        — работает
#
# Без from_queryset пришлось бы писать обёртки для КАЖДОГО метода.
# ==============================================================================

from django.db import models

from apps.catalog.querysets.product_queryset import ProductQuerySet


class ProductManager(models.Manager.from_queryset(ProductQuerySet)):
    """
    Менеджер товара.

    Все QuerySet-методы доступны напрямую:
        Product.objects.active()
        Product.objects.catalog()
        Product.objects.search('iphone')
    благодаря from_queryset(ProductQuerySet).

    Прокси-методы не нужны — from_queryset делает всё автоматически.
    """
    pass  # Пустой класс — вся магия в from_queryset()
