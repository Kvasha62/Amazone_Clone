"""
Фикстуры и утилиты для тестов пользователей.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from apps.users.models import UserProfile, Address

User = get_user_model()


class UserTestCase(TestCase):
    """
    Базовый класс для тестов пользователей.

    Создаёт:
      - 1 пользователь (testuser)
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            first_name='Иван',
            last_name='Тестов',
        )

    def _create_user(self, *, username, email, password='TestPass123!', **kwargs):
        """Создаёт пользователя с профилем."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **kwargs,
        )
        UserProfile.objects.get_or_create(user=user)
        return user

    def _create_address(self, user=None, **kwargs):
        """Создаёт адрес доставки."""
        if user is None:
            user = self.user
        defaults = {
            'recipient_name': 'Иван Тестов',
            'city': 'Москва',
            'street': 'ул. Тестовая, д. 1',
            'country': 'Россия',
            'postal_code': '123456',
        }
        defaults.update(kwargs)
        return Address.objects.create(user=user, **defaults)
