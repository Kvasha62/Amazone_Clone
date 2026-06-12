# ────────────────────────────────────────────────────────────────────────
# apps/pricing/querysets/price_queryset.py — QuerySet для модели Price.
#
# Методы для фильтрации цен по варианту, скидкам, товару.
# Доступны через Price.objects.* благодаря from_queryset().
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/
# ────────────────────────────────────────────────────────────────────────

from django.db import models


class PriceQuerySet(models.QuerySet):
    """QuerySet-методы для Price."""

    def for_variant(self, variant):
        """
        Цена конкретного варианта.
        Обычно не нужен — variant.price (OneToOne) быстрее.
        Полезен для QuerySet-композиции в сложных запросах.
        """
        return self.filter(variant=variant)

    def on_sale(self):
        """
        Только варианты со скидкой (sale_price IS NOT NULL).

        sale_price__isnull=False → WHERE sale_price IS NOT NULL.
        Без: чтобы найти скидки нужно итерировать все цены.
        """
        return self.filter(sale_price__isnull=False)

    def min_price_gte(self, value):
        """
        Фильтр по минимальной базовой цене.
        price__gte=value → WHERE price >= value.
        """
        return self.filter(price__gte=value)

    def for_product(self, product):
        """
        Все цены вариантов данного товара.

        variant__product=product — навигация через FK:
          Price → variant (FK к ProductVariant) → product (FK к Product)
        Django транслирует в:
          SELECT pricing_price.* FROM pricing_price
          INNER JOIN catalog_productvariant ON ...
          WHERE catalog_productvariant.product_id = X

        Полезно для аналитики: все цены одного товара в одном запросе.
        """
        return self.filter(variant__product=product)
