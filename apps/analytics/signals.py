# ────────────────────────────────────────────────────────────────────────
# apps/analytics/signals.py — сигналы модуля аналитики.
# ────────────────────────────────────────────────────────────────────────

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.analytics.models import ProductView

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ProductView)
def on_product_view_saved(sender, instance, created, **kwargs):
    """
    Сигнал при сохранении просмотра товара.

    При создании — логирует запись просмотра.
    """
    if created:
        logger.info(
            'product_view_signal',
            extra={
                'view_id': instance.pk,
                'product_id': instance.product_id,
                'source': instance.source,
            },
        )
