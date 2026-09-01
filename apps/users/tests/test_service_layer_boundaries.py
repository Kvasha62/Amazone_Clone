# ────────────────────────────────────────────────────────────────────────
# PROD-002 regression: User auth/password mutations go through UserService.
# ────────────────────────────────────────────────────────────────────────

import inspect

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.users.api_views import auth_views, password_reset_views
from apps.users.services.user_service import UserService
from apps.users.tests.factories import UserTestCase


class AuthViewsServiceBoundarySourceTests(SimpleTestCase):
    """Entrypoints must not call ORM User mutations directly."""

    def test_register_view_delegates_to_user_service(self):
        source = inspect.getsource(auth_views.RegisterView.post)
        self.assertIn('UserService.register', source)
        self.assertNotIn('objects.create_user', source)
        self.assertNotIn('.save(', source)

    def test_change_password_view_delegates_to_user_service(self):
        source = inspect.getsource(auth_views.ChangePasswordView.post)
        self.assertIn('UserService.change_password', source)
        self.assertNotIn('set_password', source)
        self.assertNotIn('.save(', source)

    def test_password_reset_confirm_delegates_to_user_service(self):
        source = inspect.getsource(password_reset_views.PasswordResetConfirmView.post)
        self.assertIn('UserService.reset_password', source)
        self.assertNotIn('user.set_password', source)
        self.assertNotIn("user.save(", source)


class AuthViewsServiceBoundaryBehaviorTests(UserTestCase):
    """Behavior stays the same after routing through UserService."""

    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user_and_profile_via_service(self):
        resp = self.client.post(
            '/api/v1/auth/register/',
            {
                'email': 'boundary@example.com',
                'username': 'boundary_user',
                'password': 'StrongPass123!',
                'password_confirm': 'StrongPass123!',
                'first_name': 'Bound',
                'last_name': 'Ary',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        from apps.users.models import User, UserProfile

        user = User.objects.get(email='boundary@example.com')
        self.assertTrue(user.check_password('StrongPass123!'))
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_change_password_uses_service(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            '/api/v1/auth/change-password/',
            {
                'old_password': 'TestPass123!',
                'new_password': 'BrandNewPass9!',
                'new_password_confirm': 'BrandNewPass9!',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass9!'))


class UserServiceResetPasswordTests(TestCase):
    def test_reset_password_sets_new_hash(self):
        from apps.users.models import User

        user = User.objects.create_user(
            username='resetme',
            email='resetme@example.com',
            password='OldPass123!',
        )
        UserService.reset_password(user, new_password='FreshPass456!')
        user.refresh_from_db()
        self.assertTrue(user.check_password('FreshPass456!'))
        self.assertFalse(user.check_password('OldPass123!'))
