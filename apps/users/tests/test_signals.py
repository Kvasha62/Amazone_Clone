"""
Тесты сигналов пользователей.
"""
import weakref

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase

from apps.users.models import UserProfile
from apps.users.signals import create_user_profile

User = get_user_model()


class UserProfileSignalTests(TestCase):

    def test_signal_function_exists(self):
        self.assertTrue(hasattr(create_user_profile, '__name__'))

    def test_signal_connected_to_post_save(self):
        """create_user_profile подключена к post_save для User."""
        found = False
        for entry in post_save.receivers:
            for item in entry:
                if isinstance(item, weakref.ref):
                    func = item()
                elif callable(item):
                    func = item
                else:
                    continue
                if func is not None and getattr(func, '__name__', '') == 'create_user_profile':
                    found = True
                    break
            if found:
                break
        self.assertTrue(found, 'create_user_profile не подключена к post_save')

    def test_profile_auto_created_on_user_creation(self):
        """Профиль создаётся автоматически при создании User."""
        user = User.objects.create_user(
            username='signal_test',
            email='signal@example.com',
            password='pass123!',
        )
        self.assertTrue(
            UserProfile.objects.filter(user=user).exists(),
            'Профиль не был создан автоматически через сигнал',
        )

    def test_profile_not_recreated_on_save(self):
        """Повторный save не создаёт второй профиль."""
        user = User.objects.create_user(
            username='signal_resave',
            email='resave@example.com',
            password='pass123!',
        )
        user.save()  # повторный save
        self.assertEqual(
            UserProfile.objects.filter(user=user).count(), 1,
        )
