from django.test import TestCase
from apps.orders.tests.factories import create_test_user
from apps.notifications.tests.factories import create_test_notification
from apps.notifications.models import Notification


class NotificationModelTests(TestCase):

    def setUp(self):
        self.user = create_test_user()

    def test_create(self):
        n = create_test_notification(self.user)
        self.assertIsNotNone(n.pk)
        self.assertEqual(n.user, self.user)
        self.assertEqual(n.notification_type, 'system')
        self.assertEqual(n.status, 'pending')

    def test_str(self):
        n = create_test_notification(self.user)
        self.assertIn(str(self.user.pk), str(n))

    def test_is_read_false(self):
        n = create_test_notification(self.user)
        self.assertFalse(n.is_read)

    def test_is_read_true(self):
        from django.utils import timezone
        n = create_test_notification(self.user)
        n.read_at = timezone.now()
        n.save()
        self.assertTrue(n.is_read)


class NotificationManagerTests(TestCase):

    def setUp(self):
        self.user = create_test_user()
        self.user2 = create_test_user()
        self.n1 = create_test_notification(self.user, title='Unread')
        self.n2 = create_test_notification(self.user, title='Read')
        from django.utils import timezone
        self.n2.read_at = timezone.now()
        self.n2.save()

    def test_for_user(self):
        qs = Notification.objects.for_user(self.user)
        self.assertEqual(qs.count(), 2)

    def test_unread(self):
        qs = Notification.objects.unread()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.n1)

    def test_read(self):
        qs = Notification.objects.read()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.n2)

    def test_by_type(self):
        create_test_notification(self.user, notification_type='order_created')
        qs = Notification.objects.by_type('order_created')
        self.assertEqual(qs.count(), 1)

    def test_pending(self):
        qs = Notification.objects.pending()
        self.assertEqual(qs.count(), 2)
