"""
Тесты моделей пользователей.
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.users.models import User, UserProfile, Address
from apps.users.tests.factories import UserTestCase


class UserModelTests(UserTestCase):

    def test_create_user(self):
        user = self.user
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('TestPass123!'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_email_unique(self):
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='duplicate',
                email='test@example.com',
                password='pass',
            )

    def test_username_unique(self):
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='testuser',
                email='other@example.com',
                password='pass',
            )

    def test_str_returns_email(self):
        self.assertEqual(str(self.user), 'test@example.com')

    def test_full_name(self):
        self.assertEqual(self.user.full_name, 'Иван Тестов')

    def test_full_name_fallback_to_email(self):
        user = User.objects.create_user(
            username='nofirstname',
            email='nofirst@example.com',
            password='pass',
        )
        self.assertEqual(user.full_name, 'nofirst@example.com')

    def test_ordering(self):
        self.assertEqual(User._meta.ordering, ('-date_joined',))

    def test_phone_default_empty(self):
        self.assertEqual(self.user.phone, '')

    def test_normalize_email(self):
        user = User.objects.create_user(
            username='normemail',
            email='Test@EXAMPLE.com',
            password='pass',
        )
        # Django нормализует доменную часть
        self.assertNotEqual(user.email, 'Test@EXAMPLE.com')


class UserProfileModelTests(UserTestCase):

    def test_profile_auto_created(self):
        """Профиль создаётся автоматически при создании User (сигнал)."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)

    def test_profile_str(self):
        self.assertIn('test@example.com', str(self.user.profile))

    def test_profile_defaults(self):
        profile = self.user.profile
        self.assertEqual(profile.timezone, 'UTC')
        self.assertEqual(profile.language, 'ru')
        self.assertFalse(profile.email_subscribed)
        self.assertFalse(profile.avatar)
        self.assertIsNone(profile.date_of_birth)
        self.assertEqual(profile.gender, '')

    def test_one_to_one_constraint(self):
        """Нельзя создать второй профиль для того же пользователя."""
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)

    def test_ordering(self):
        self.assertEqual(UserProfile._meta.ordering, ('-created_at',))


class AddressModelTests(UserTestCase):

    def setUp(self):
        self.address = self._create_address()

    def test_create_address(self):
        self.assertEqual(self.address.city, 'Москва')
        self.assertEqual(self.address.recipient_name, 'Иван Тестов')
        self.assertFalse(self.address.is_default)

    def test_str_representation(self):
        addr_str = str(self.address)
        self.assertIn('Москва', addr_str)
        self.assertIn('ул. Тестовая, д. 1', addr_str)

    def test_str_with_postal_code(self):
        address = self._create_address(
            city='СПб', street='Невский, 1', postal_code='190000',
        )
        addr_str = str(address)
        self.assertIn('190000', addr_str)

    def test_set_default_unsets_others(self):
        """При is_default=True другие адреса теряют default."""
        addr1 = self._create_address(city='Москва', is_default=True)
        addr2 = self._create_address(city='Казань', is_default=True)

        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)

    def test_default_country(self):
        address = self._create_address()
        self.assertEqual(address.country, 'Россия')

    def test_empty_recipient_name_constraint(self):
        """recipient_name не может быть пустым (CheckConstraint)."""
        with self.assertRaises(IntegrityError):
            Address.objects.create(
                user=self.user,
                recipient_name='',
                city='Москва',
                street='ул. Пустая, 1',
            )

    def test_ordering(self):
        self.assertEqual(
            Address._meta.ordering,
            ('-is_default', '-created_at'),
        )

    def test_cascade_delete_user_deletes_addresses(self):
        """При удалении пользователя адреса удаляются каскадом."""
        self._create_address()
        self._create_address(city='СПб')
        user_id = self.user.pk
        self.user.delete()
        self.assertEqual(Address.objects.filter(user_id=user_id).count(), 0)
