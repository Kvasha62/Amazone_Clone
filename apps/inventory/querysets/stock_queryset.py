# ────────────────────────────────────────────────────────────────────────
# apps/inventory/querysets/stock_queryset.py — кастомный QuerySet для Stock.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Stock.objects.in_stock() → AttributeError
#   • Stock.objects.low_stock() → AttributeError
# ────────────────────────────────────────────────────────────────────────

from django.db import models


class StockQuerySet(models.QuerySet):
    """
    Кастомный QuerySet с методами для частых запросов к остаткам.
    Поддерживает chaining: Stock.objects.in_stock().for_product(product)
    """

    def in_stock(self):
        """
        Варианты, которые есть в наличии (quantity > 0).
        Используется в каталоге для фильтра «в наличии».
        """
        return self.filter(quantity__gt=0)

    def out_of_stock(self):
        """Варианты, которых нет на складе (quantity = 0)."""
        return self.filter(quantity=0)

    def low_stock(self):
        """
        Варианты с низким остатком.
        quantity ≤ low_stock_threshold → нужно заказывать у поставщика.
        """
        return self.filter(
            quantity__lte=models.F('low_stock_threshold'),
            quantity__gt=0,  # Не показываем полностью отсутствующие
        )

    def has_available(self):
        """
        Варианты, которые можно заказать (available > 0).
        available = quantity - reserved > 0
        """
        return self.filter(
            quantity__gt=models.F('reserved_quantity'),
        )

    def for_product(self, product):
        """
        Остатки всех вариантов конкретного товара.
        Используется в карточке товара.
        """
        return self.filter(variant__product=product)

    def with_variant(self):
        """
        Подгружает вариант и товар (select_related).
        Без: stock.variant.product.name → 3 SQL-запроса на каждый stock.
        """
        return self.select_related(
            'variant',
            'variant__product',
        )
