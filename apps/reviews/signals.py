# ────────────────────────────────────────────────────────────────────────
# apps/reviews/signals.py — логирование событий отзывов.
# ────────────────────────────────────────────────────────────────────────

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.reviews.models import Review

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Review)
def on_review_saved(sender, instance: Review, created: bool, **kwargs):
    if created:
        logger.info(
            'review_created_signal',
            extra={
                'review_id': instance.pk,
                'user_id': instance.user_id,
                'product_id': instance.product_id,
                'rating': instance.rating,
            },
        )


@receiver(post_delete, sender=Review)
def on_review_deleted(sender, instance: Review, **kwargs):
    logger.info(
        'review_deleted_signal',
        extra={
            'review_id': instance.pk,
            'product_id': instance.product_id,
        },
    )
