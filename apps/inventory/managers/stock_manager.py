# ────────────────────────────────────────────────────────────────────────
# apps/inventory/managers/stock_manager.py — кастомный менеджер для Stock.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Stock.objects.in_stock() → AttributeError
#   • Stock.objects.low_stock() → AttributeError
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.inventory.querysets.stock_queryset import StockQuerySet


class StockManager(models.Manager.from_queryset(StockQuerySet)):
    """
    Кастомный менеджер для Stock с методами из StockQuerySet.

    📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#creating-a-manager-with-queryset-methods
    """
    pass
