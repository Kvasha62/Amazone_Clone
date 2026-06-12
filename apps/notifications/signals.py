import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def on_notification_saved(sender, instance, created, **kwargs):
    if created:
        logger.info(
            'notification_created_signal',
            extra={'notif_id': instance.pk, 'user_id': instance.user_id},
        )
