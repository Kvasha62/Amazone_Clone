# ────────────────────────────────────────────────────────────────────────
# PROD-002 regression: notification tasks mutate via NotificationService.
# ────────────────────────────────────────────────────────────────────────

import inspect

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.notifications import tasks as notification_tasks
from apps.notifications.constants import CHANNEL_EMAIL, STATUS_PENDING, STATUS_SENT
from apps.notifications.models import Notification
from apps.notifications.services.notification_service import NotificationService
from apps.orders.tests.factories import create_test_order, create_test_user


class NotificationTasksSourceBoundaryTests(SimpleTestCase):
    def test_send_email_notification_uses_mark_sent(self):
        source = inspect.getsource(notification_tasks.send_email_notification)
        self.assertIn('NotificationService.mark_sent', source)
        self.assertNotIn('.save(', source)

    def test_send_order_confirmation_uses_service_create(self):
        source = inspect.getsource(notification_tasks.send_order_confirmation)
        self.assertIn('NotificationService.create', source)
        self.assertNotIn('Notification.objects.create', source)

    def test_send_order_shipped_uses_service_create(self):
        source = inspect.getsource(notification_tasks.send_order_shipped)
        self.assertIn('NotificationService.create', source)
        self.assertNotIn('Notification.objects.create', source)


class NotificationTasksBehaviorTests(TestCase):
    def test_send_email_notification_marks_sent_via_service(self):
        user = create_test_user()
        notif = Notification.objects.create(
            user=user,
            notification_type='system',
            channel=CHANNEL_EMAIL,
            title='Hello',
            body='Body',
            status=STATUS_PENDING,
        )
        notification_tasks.send_email_notification(notif.pk)
        notif.refresh_from_db()
        self.assertEqual(notif.status, STATUS_SENT)
        self.assertIsNotNone(notif.sent_at)

    def test_send_order_confirmation_creates_via_service(self):
        user = create_test_user()
        order = create_test_order(user)
        # Call task body synchronously (no Celery delay).
        from unittest.mock import patch

        with patch.object(
            notification_tasks.send_email_notification,
            'delay',
            return_value=None,
        ) as delay_mock:
            notification_tasks.send_order_confirmation(order.pk)

        notif = Notification.objects.get(
            user=order.user,
            related_object_type='order',
            related_object_id=order.pk,
            notification_type='order_confirmed',
        )
        self.assertEqual(notif.channel, CHANNEL_EMAIL)
        self.assertEqual(notif.status, STATUS_PENDING)
        delay_mock.assert_called_once_with(notif.pk)

    def test_mark_sent_service_updates_fields(self):
        user = create_test_user()
        notif = NotificationService.create(
            user,
            notification_type='system',
            title='Deferred',
            channel=CHANNEL_EMAIL,
            send_immediately=False,
        )
        self.assertEqual(notif.status, STATUS_PENDING)
        before = timezone.now()
        updated = NotificationService.mark_sent(notif)
        self.assertEqual(updated.status, STATUS_SENT)
        self.assertIsNotNone(updated.sent_at)
        self.assertGreaterEqual(updated.sent_at, before)
