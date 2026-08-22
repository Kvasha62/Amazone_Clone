"""
Тесты UserService — бизнес-логика пользователей.
"""
from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from apps.users.models import User, UserProfile
from apps.users.services.user_service import UserService
from apps.users.tests.factories import UserTestCase


class RegisterTests(TestCase):

    def test_register_success(self):
        user = UserService.register(
            email='new@example.com',
            username='newuser',
            password='StrongPass123!',
        )
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.username, 'newuser')
        self.assertTrue(user.check_password('StrongPass123!'))

    def test_register_creates_profile(self):
        user = UserService.register(
            email='profile@example.com',
            username='profileuser',
            password='StrongPass123!',
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_register_duplicate_email(self):
        UserService.register(
            email='dup@example.com',
            username='user1',
            password='StrongPass123!',
        )
        with self.assertRaises(ValidationError) as ctx:
            UserService.register(
                email='dup@example.com',
                username='user2',
                password='StrongPass123!',
            )
        self.assertIn('email', ctx.exception.detail)

    def test_register_duplicate_username(self):
        UserService.register(
            email='first@example.com',
            username='sameuser',
            password='StrongPass123!',
        )
        with self.assertRaises(ValidationError) as ctx:
            UserService.register(
                email='second@example.com',
                username='sameuser',
                password='StrongPass123!',
            )
        self.assertIn('username', ctx.exception.detail)

    def test_register_email_case_insensitive(self):
        """Регистрация с тем же email в другом регистре — ошибка."""
        UserService.register(
            email='Case@Example.com',
            username='case1',
            password='StrongPass123!',
        )
        with self.assertRaises(ValidationError):
            UserService.register(
                email='case@example.com',
                username='case2',
                password='StrongPass123!',
            )

    def test_register_with_names(self):
        user = UserService.register(
            email='named@example.com',
            username='nameduser',
            password='StrongPass123!',
            first_name='Иван',
            last_name='Иванов',
        )
        self.assertEqual(user.first_name, 'Иван')
        self.assertEqual(user.last_name, 'Иванов')

    def test_register_with_phone(self):
        user = UserService.register(
            email='phone@example.com',
            username='phoneuser',
            password='StrongPass123!',
            phone='+79991234567',
        )
        self.assertEqual(user.phone, '+79991234567')


class UpdateProfileTests(UserTestCase):

    def test_update_first_name(self):
        user = UserService.update_profile(self.user, first_name='Пётр')
        self.assertEqual(user.first_name, 'Пётр')

    def test_update_last_name(self):
        user = UserService.update_profile(self.user, last_name='Сидоров')
        self.assertEqual(user.last_name, 'Сидоров')

    def test_update_phone(self):
        user = UserService.update_profile(self.user, phone='+79990000000')
        self.assertEqual(user.phone, '+79990000000')

    def test_update_profile_timezone(self):
        user = UserService.update_profile(self.user, timezone='Europe/Moscow')
        self.assertEqual(user.profile.timezone, 'Europe/Moscow')

    def test_update_profile_language(self):
        user = UserService.update_profile(self.user, language='en')
        self.assertEqual(user.profile.language, 'en')

    def test_update_profile_email_subscribed(self):
        user = UserService.update_profile(self.user, email_subscribed=True)
        self.assertTrue(user.profile.email_subscribed)

    def test_update_profile_date_of_birth(self):
        from datetime import date
        dob = date(1990, 1, 1)
        user = UserService.update_profile(self.user, date_of_birth=dob)
        self.assertEqual(user.profile.date_of_birth, dob)

    def test_update_profile_gender(self):
        user = UserService.update_profile(self.user, gender='M')
        self.assertEqual(user.profile.gender, 'M')

    def test_update_none_does_not_change(self):
        """None означает «не менять»."""
        original_name = self.user.first_name
        user = UserService.update_profile(self.user, last_name='New')
        self.assertEqual(user.first_name, original_name)
        self.assertEqual(user.last_name, 'New')


class ChangePasswordTests(UserTestCase):

    def test_change_password_success(self):
        UserService.change_password(
            self.user,
            old_password='TestPass123!',
            new_password='NewPass456!',
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_change_password_wrong_old(self):
        with self.assertRaises(ValidationError) as ctx:
            UserService.change_password(
                self.user,
                old_password='WrongOldPass!',
                new_password='NewPass456!',
            )
        self.assertIn('old_password', ctx.exception.detail)


class DeactivateTests(UserTestCase):

    def test_deactivate(self):
        UserService.deactivate(self.user)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_get_user_by_id_active_only(self):
        """get_user_by_id не находит деактивированных."""
        UserService.deactivate(self.user)
        with self.assertRaises(NotFound):
            UserService.get_user_by_id(self.user.pk)


class GetProfileTests(UserTestCase):

    def test_get_profile(self):
        profile = UserService.get_profile(self.user)
        self.assertIsInstance(profile, UserProfile)

    def test_get_profile_missing(self):
        """Если профиль удалён — NotFound."""
        self.user.profile.delete()
        with self.assertRaises(NotFound):
            UserService.get_profile(self.user)
