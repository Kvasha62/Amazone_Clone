from apps.notifications.models import Notification


def create_test_notification(
    user,
    *,
    notification_type='system',
    title='Test notification',
    body='Test body',
    channel='in_app',
    status='pending',
    related_object_type='',
    related_object_id=None,
):
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        channel=channel,
        status=status,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
    )
