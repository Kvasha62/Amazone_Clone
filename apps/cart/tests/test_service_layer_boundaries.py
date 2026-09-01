# ────────────────────────────────────────────────────────────────────────
# PROD-002 regression: cart cleanup / admin deactivate via CartService.
# ────────────────────────────────────────────────────────────────────────

import inspect
from datetime import timedelta

from django.contrib.admin.sites import AdminSite
from django.test import SimpleTestCase, RequestFactory
from django.utils import timezone

from apps.cart.admin.cart_admin import CartAdmin
from apps.cart.management.commands import cleanup_expired_carts as cleanup_cmd
from apps.cart.models import Cart
from apps.cart.services.cart_service import CartService
from apps.cart.tests.factories import CartTestCase


class CartCleanupSourceBoundaryTests(SimpleTestCase):
    def test_cleanup_command_delegates_to_service(self):
        source = inspect.getsource(cleanup_cmd.Command.handle)
        self.assertIn('CartService.cleanup_expired_carts', source)
        self.assertNotIn('.delete()', source)
        self.assertNotIn('.update(', source)

    def test_cart_admin_deactivate_delegates_to_service(self):
        source = inspect.getsource(CartAdmin.deactivate_selected)
        self.assertIn('CartService.deactivate_carts', source)
        self.assertNotIn('queryset.update', source)


class CartCleanupBehaviorTests(CartTestCase):
    def _make_old(self, cart, days_ago=60):
        Cart.objects.filter(pk=cart.pk).update(
            updated_at=timezone.now() - timedelta(days=days_ago),
        )
        cart.refresh_from_db()

    def test_service_cleanup_deletes_old_inactive(self):
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('svc-old-inactive'),
            is_active=False,
        )
        self._make_old(cart, days_ago=60)

        result = CartService.cleanup_expired_carts(
            inactive_days=30,
            guest_stale_days=14,
            dry_run=False,
        )
        self.assertEqual(result['inactive_deleted'], 1)
        self.assertFalse(Cart.objects.filter(pk=cart.pk).exists())

    def test_service_cleanup_deactivates_stale_guest(self):
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('svc-stale-guest'),
            is_active=True,
        )
        self._make_old(cart, days_ago=20)

        result = CartService.cleanup_expired_carts(
            inactive_days=30,
            guest_stale_days=14,
            dry_run=False,
        )
        self.assertEqual(result['guest_deactivated'], 1)
        cart.refresh_from_db()
        self.assertFalse(cart.is_active)

    def test_command_still_works_via_service(self):
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('cmd-via-svc'),
            is_active=False,
        )
        self._make_old(cart, days_ago=60)
        cleanup_cmd.Command().handle(
            dry_run=False, inactive_days=30, guest_stale_days=14,
        )
        self.assertFalse(Cart.objects.filter(pk=cart.pk).exists())

    def test_admin_deactivate_selected_uses_service(self):
        from unittest.mock import patch

        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('admin-deact'),
            is_active=True,
        )
        admin = CartAdmin(Cart, AdminSite())
        request = RequestFactory().post('/admin/')
        request.user = self.user
        qs = Cart.objects.filter(pk=cart.pk)
        # message_user needs MessageMiddleware; stub it for unit isolation.
        with patch.object(admin, 'message_user'):
            admin.deactivate_selected(request, qs)
        cart.refresh_from_db()
        self.assertFalse(cart.is_active)
