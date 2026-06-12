# ────────────────────────────────────────────────────────────────────────
# apps/pricing/signals.py — сигналы пересчёта Product.min_price/max_price.
#
# При сохранении/удалении Price → пересчитывает денормализованные
# min_price и max_price на связанном товаре (Product).
#
# ПОЧЕМУ СИГНАЛЫ ЗДЕСЬ, А НЕ В CATALOG:
#   Сигнал подключён к sender=Price (модуль pricing).
#   Логически: «когда цена меняется → товар обновляется».
#   Альтернатива: вызов recalculate_product_prices() в сервисе.
#   Но сигнал защищает от прямых ORM-вызовов:
#     Price.objects.filter(variant=v).update(price=100)
#   Без сигнала → min/max не обновятся.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/signals/
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#post-save
# ────────────────────────────────────────────────────────────────────────

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.pricing.models import Price

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=Price) — вызывается после Price.save().
# Срабатывает и при create, и при update.
@receiver(post_save, sender=Price)
def recalculate_on_price_save(sender, instance, **kwargs):
    """
    Пересчитывает min_price / max_price товара при изменении цены.

    ПОЧЕМУ __import__ ВМЕСТО ПРЯМОГО ИМПОРТА:
      Циклический импорт:
        signals → PricingService → Price (models) → signals (через ready())
      __import__ — lazy-подход: импортирует при вызове, не при загрузке.
      Альтернатива: переместить recalculate_product_prices() в catalog app.
    """
    try:
        product = instance.variant.product
        # __import__ — динамический импорт. Разрывает циклическую зависимость.
        # 📖 https://docs.python.org/3/library/functions.html#__import__
        PricingService = __import__(
            'apps.pricing.services.pricing_service',
            fromlist=['PricingService'],
        ).PricingService
        PricingService.recalculate_product_prices(product)
    except Exception:
        # Не ломаем сохранение цены если пересчёт упал.
        # Сценарий: variant.product = None (редкий edge case).
        # logger.exception — логирует полный traceback.
        logger.exception('Failed to recalculate product prices')


@receiver(post_delete, sender=Price)
def recalculate_on_price_delete(sender, instance, **kwargs):
    """
    Пересчитывает min_price / max_price товара при удалении цены.

    СЦЕНАРИЙ: Price.objects.filter(variant=v).delete()
    Удаление цены варианта → min/max может измениться.
    """
    try:
        product = instance.variant.product
        PricingService = __import__(
            'apps.pricing.services.pricing_service',
            fromlist=['PricingService'],
        ).PricingService
        PricingService.recalculate_product_prices(product)
    except Exception:
        logger.exception('Failed to recalculate product prices after deletion')
