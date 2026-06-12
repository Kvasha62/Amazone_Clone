# ────────────────────────────────────────────────────────────────────────
# apps/pricing/managers/price_manager.py — менеджер модели Price.
#
# from_queryset(PriceQuerySet) → методы for_variant, on_sale, for_product
# доступны через Price.objects.*.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#from-queryset
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.pricing.querysets.price_queryset import PriceQuerySet


class PriceManager(models.Manager.from_queryset(PriceQuerySet)):
    """
    Менеджер цены с QuerySet-методами:
      Price.objects.for_variant(variant)
      Price.objects.on_sale()
      Price.objects.for_product(product)
    """
    pass
