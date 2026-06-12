"""
Тесты QuerySet корзины.
"""
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.cart.tests.factories import CartTestCase


class CartQuerySetTests(CartTestCase):

    def setUp(self):
        self.cart = self._create_cart()
        self.inactive_cart = Cart.objects.create(
            user=None,
            session_key_hash=Cart.hash_session_key('inactive-session'),
            is_active=False,
        )

    def test_active_returns_only_active(self):
        qs = Cart.objects.active()
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.cart.pk, pks)
        self.assertNotIn(self.inactive_cart.pk, pks)

    def test_for_user(self):
        qs = Cart.objects.for_user(self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().user, self.user)

    def test_for_user_excludes_inactive(self):
        Cart.objects.create(user=self.user, is_active=False)
        qs = Cart.objects.for_user(self.user)
        self.assertEqual(qs.count(), 1)

    def test_for_session(self):
        session_hash = Cart.hash_session_key('guest-qs-test')
        Cart.objects.create(session_key_hash=session_hash, is_active=True)
        qs = Cart.objects.for_session(session_hash)
        self.assertEqual(qs.count(), 1)

    def test_with_items_prefetch(self):
        self._add_item(self.cart, self.variant_a)
        self._add_item(self.cart, self.variant_b)
        cart = Cart.objects.with_items().get(pk=self.cart.pk)
        items = cart.items.all()
        self.assertEqual(len(items), 2)

    def test_full_returns_active_with_items(self):
        self._add_item(self.cart, self.variant_a)
        cart = Cart.objects.full().get(pk=self.cart.pk)
        self.assertEqual(cart.items.count(), 1)

    def test_full_excludes_inactive(self):
        self._add_item(self.inactive_cart, self.variant_a)
        qs = Cart.objects.full()
        pks = list(qs.values_list('pk', flat=True))
        self.assertNotIn(self.inactive_cart.pk, pks)
