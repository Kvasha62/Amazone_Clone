import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.wishlist.models import Wishlist

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Wishlist)
def on_wishlist_saved(sender, instance, created, **kwargs):
    if created:
        logger.info(
            'wishlist_created_signal',
            extra={'wishlist_id': instance.pk, 'user_id': instance.user_id},
        )
