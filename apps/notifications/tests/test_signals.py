from django.test import TestCase
from apps.orders.tests.factories import create_test_user
from apps.notifications.services.notification_service import NotificationService


class NotificationSignalTests(TestCase):

    def test_signal_on_create(self):
        user = create_test_user()
        with self.assertLogs('apps.notifications.signals', level='INFO') as cm:
            NotificationService.create(
                user,
                notification_type='system',
                title='Signal test',
                send_immediately=False,
            )
        self.assertTrue(
            any('notification_created_signal' in m for m in cm.output)
        )
