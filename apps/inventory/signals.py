# ────────────────────────────────────────────────────────────────────────
# apps/inventory/signals.py — сигналы модуля склада.
#
# НАЗНАЧЕНИЕ:
#   Логирование изменений остатков и уведомления о «мало товара».
#
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#post-save
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Логирование изменений стока не работает
#   • Уведомления о «мало товара» не отправляются
# ────────────────────────────────────────────────────────────────────────

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='inventory.Stock')
def on_stock_saved(sender, instance, created, **kwargs):
    """
    Обработчик post_save для Stock.

    ДЕЙСТВИЯ:
      • created → логирует создание записи остатков
      • !created → логирует обновление + проверяет low stock
    """
    if created:
        logger.info(
            'stock_created',
            extra={
                'stock_id': instance.pk,
                'variant_id': instance.variant_id,
                'quantity': instance.quantity,
            },
        )
    else:
        logger.debug(
            'stock_updated',
            extra={
                'stock_id': instance.pk,
                'variant_id': instance.variant_id,
                'quantity': instance.quantity,
                'reserved': instance.reserved_quantity,
            },
        )

        # Проверяем low stock — если остаток упал до порога.
        if instance.is_low_stock and not instance.is_out_of_stock:
            logger.warning(
                'low_stock_alert',
                extra={
                    'stock_id': instance.pk,
                    'variant_id': instance.variant_id,
                    'quantity': instance.quantity,
                    'threshold': instance.low_stock_threshold,
                },
            )


@receiver(post_save, sender='inventory.StockMovement')
def on_stock_movement_created(sender, instance, created, **kwargs):
    """
    Обработчик post_save для StockMovement.
    Логирует каждое новое движение.
    """
    if created:
        logger.info(
            'stock_movement_created',
            extra={
                'movement_id': instance.pk,
                'kind': instance.kind,
                'delta': instance.delta,
                'stock_id': instance.stock_id,
                'qty_before': instance.quantity_before,
                'qty_after': instance.quantity_after,
            },
        )
