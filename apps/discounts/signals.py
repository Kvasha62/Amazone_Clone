import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.discounts.models import Coupon

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Coupon)
def on_coupon_saved(sender, instance, created, **kwargs):
    if created:
        logger.info(
            'coupon_created_signal',
            extra={'coupon_id': instance.pk, 'code': instance.code},
        )
