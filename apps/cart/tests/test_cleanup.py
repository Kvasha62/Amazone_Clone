"""
Тесты management-команды cleanup_expired_carts.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.cart.models import Cart, CartItem
from apps.cart.tests.factories import CartTestCase


class CleanupExpiredCartsTests(CartTestCase):
    """Тесты для manage.py cleanup_expired_carts."""

    def _make_old(self, cart, days_ago=60):
        """Устанавливает updated_at в прошлое."""
        Cart.objects.filter(pk=cart.pk).update(
            updated_at=timezone.now() - timedelta(days=days_ago),
        )
        cart.refresh_from_db()

    def test_cleanup_deletes_old_inactive_carts(self):
        """Неактивные корзины старше TTL — удаляются."""
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('old-inactive'),
            is_active=False,
        )
        self._make_old(cart, days_ago=60)

        from apps.cart.management.commands.cleanup_expired_carts import Command
        cmd = Command()
        cmd.handle(dry_run=False, inactive_days=30, guest_stale_days=14)

        self.assertFalse(Cart.objects.filter(pk=cart.pk).exists())

    def test_cleanup_dry_run_does_not_delete(self):
        """--dry-run не удаляет."""
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('dry-run-cart'),
            is_active=False,
        )
        self._make_old(cart, days_ago=60)

        from apps.cart.management.commands.cleanup_expired_carts import Command
        cmd = Command()
        cmd.handle(dry_run=True, inactive_days=30, guest_stale_days=14)

        self.assertTrue(Cart.objects.filter(pk=cart.pk).exists())

    def test_cleanup_keeps_recent_inactive(self):
        """Недавно деактивированная корзина не удаляется."""
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('recent-inactive'),
            is_active=False,
        )
        # updated_at = сейчас (только что создана)

        from apps.cart.management.commands.cleanup_expired_carts import Command
        cmd = Command()
        cmd.handle(dry_run=False, inactive_days=30, guest_stale_days=14)

        self.assertTrue(Cart.objects.filter(pk=cart.pk).exists())

    def test_cleanup_deactivates_stale_guest_carts(self):
        """Старые гостевые корзины помечаются неактивными."""
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('stale-guest'),
            is_active=True,
        )
        self._make_old(cart, days_ago=20)

        from apps.cart.management.commands.cleanup_expired_carts import Command
        cmd = Command()
        cmd.handle(dry_run=False, inactive_days=30, guest_stale_days=14)

        cart.refresh_from_db()
        self.assertFalse(cart.is_active)

    def test_cleanup_keeps_active_user_cart(self):
        """Активная корзина пользователя не деактивируется."""
        cart = self._create_cart()
        self._make_old(cart, days_ago=20)

        from apps.cart.management.commands.cleanup_expired_carts import Command
        cmd = Command()
        cmd.handle(dry_run=False, inactive_days=30, guest_stale_days=14)

        cart.refresh_from_db()
        self.assertTrue(cart.is_active)

    def test_cleanup_cascades_items(self):
        """При удалении корзины удаляются и её позиции."""
        cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('cascade-cart'),
            is_active=False,
        )
        self._add_item(cart, self.variant_a, 1)
        self._add_item(cart, self.variant_b, 2)
        self._make_old(cart, days_ago=60)

        from apps.cart.management.commands.cleanup_expired_carts import Command
        cmd = Command()
        cmd.handle(dry_run=False, inactive_days=30, guest_stale_days=14)

        self.assertFalse(Cart.objects.filter(pk=cart.pk).exists())
        self.assertEqual(CartItem.objects.filter(cart__pk=cart.pk).count(), 0)
