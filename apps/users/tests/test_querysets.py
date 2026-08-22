"""
Тесты QuerySet пользователя.
"""
from django.test import TestCase

from apps.users.models import User, UserProfile
from apps.users.tests.factories import UserTestCase


class UserQuerySetTests(UserTestCase):

    def test_with_profile_select_related(self):
        """with_profile() подтягивает профиль без N+1."""
        qs = User.objects.with_profile()
        user = qs.get(pk=self.user.pk)
        # Доступ к профилю без дополнительного запроса
        with self.assertNumQueries(0):
            _ = user.profile

    def test_active_excludes_inactive(self):
        User.objects.create_user(
            username='inactive_user',
            email='inactive@example.com',
            password='pass',
            is_active=False,
        )
        qs = User.objects.active()
        self.assertTrue(qs.filter(pk=self.user.pk).exists())
        self.assertFalse(qs.filter(username='inactive_user').exists())

    def test_by_email_case_insensitive(self):
        qs = User.objects.by_email('TEST@EXAMPLE.COM')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.user)

    def test_by_email_no_match(self):
        qs = User.objects.by_email('nonexistent@example.com')
        self.assertEqual(qs.count(), 0)

    def test_with_addresses_prefetch(self):
        from apps.users.models import Address
        Address.objects.create(
            user=self.user,
            recipient_name='Иван',
            city='Москва',
            street='ул. 1',
        )
        user = User.objects.with_addresses().get(pk=self.user.pk)
        with self.assertNumQueries(0):
            self.assertEqual(user.addresses.count(), 1)

    def test_full_loads_profile_and_addresses(self):
        from apps.users.models import Address
        Address.objects.create(
            user=self.user,
            recipient_name='Иван',
            city='Москва',
            street='ул. 1',
        )
        user = User.objects.full().get(pk=self.user.pk)
        with self.assertNumQueries(0):
            _ = user.profile
        with self.assertNumQueries(0):
            _ = list(user.addresses.all())
