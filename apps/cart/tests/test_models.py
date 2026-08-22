"""
Тесты моделей корзины.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.cart.constants import MAX_ITEM_QUANTITY
from apps.cart.models import Cart, CartItem
from apps.cart.tests.factories import CartTestCase


class CartModelTests(CartTestCase):

    def test_create_user_cart(self):
        cart = self._create_cart()
        self.assertEqual(cart.user, self.user)
        self.assertTrue(cart.is_active)

    def test_create_guest_cart(self):
        cart = self._create_cart(user=None)
        self.assertIsNone(cart.user)
        self.assertTrue(cart.session_key_hash)
        self.assertTrue(cart.is_active)

    def test_hash_session_key_deterministic(self):
        h1 = Cart.hash_session_key('abc123')
        h2 = Cart.hash_session_key('abc123')
        self.assertEqual(h1, h2)

    def test_hash_session_key_different_inputs(self):
        h1 = Cart.hash_session_key('abc123')
        h2 = Cart.hash_session_key('xyz789')
        self.assertNotEqual(h1, h2)

    def test_hash_session_key_length(self):
        h = Cart.hash_session_key('test')
        self.assertEqual(len(h), 64)  # SHA-256 hex

    def test_hash_session_key_empty_string(self):
        """Пустая строка — тоже валидный хэш (не должно падать)."""
        h = Cart.hash_session_key('')
        self.assertEqual(len(h), 64)

    def test_unique_active_user_cart(self):
        self._create_cart(user=self.user)
        with self.assertRaises(IntegrityError):
            Cart.objects.create(user=self.user, is_active=True)

    def test_user_can_have_inactive_carts(self):
        Cart.objects.create(user=self.user, is_active=True)
        Cart.objects.create(user=self.user, is_active=False)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 2)

    def test_owner_required_constraint(self):
        """Cart без user и без session_key_hash — IntegrityError."""
        with self.assertRaises(IntegrityError):
            Cart.objects.create(is_active=True)

    def test_clean_no_owner(self):
        cart = Cart()
        with self.assertRaises(ValidationError):
            cart.clean()

    def test_str_user_cart(self):
        cart = self._create_cart()
        self.assertIn('Корзина пользователя', str(cart))

    def test_str_guest_cart(self):
        cart = self._create_cart(user=None)
        self.assertIn('Гостевая корзина', str(cart))

    def test_str_guest_cart_shows_hash_prefix(self):
        """__str__ гостевой корзины содержит первые 8 символов хэша."""
        cart = self._create_cart(user=None, session_key='hash-test-session')
        expected_prefix = Cart.hash_session_key('hash-test-session')[:8]
        self.assertIn(expected_prefix, str(cart))

    def test_ordering(self):
        self.assertEqual(Cart._meta.ordering, ('-created_at',))

    def test_cart_created_at_auto_set(self):
        """created_at заполняется автоматически."""
        cart = self._create_cart()
        self.assertIsNotNone(cart.created_at)

    def test_cart_updated_at_auto_set(self):
        """updated_at заполняется автоматически."""
        cart = self._create_cart()
        self.assertIsNotNone(cart.updated_at)

    def test_cart_is_active_default(self):
        """Новая корзина активна по умолчанию."""
        cart = self._create_cart()
        self.assertTrue(cart.is_active)


class CartItemModelTests(CartTestCase):

    def setUp(self):
        self.cart = self._create_cart()

    def test_create_item(self):
        item = self._add_item(self.cart, self.variant_a, quantity=2)
        self.assertEqual(item.quantity, 2)

    def test_unique_cart_variant(self):
        self._add_item(self.cart, self.variant_a, quantity=1)
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart, variant=self.variant_a, quantity=2,
            )

    def test_quantity_gte_1_constraint(self):
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart, variant=self.variant_a, quantity=0,
            )

    def test_quantity_lte_max_constraint(self):
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart,
                variant=self.variant_a,
                quantity=MAX_ITEM_QUANTITY + 1,
            )

    def test_quantity_max_boundary_valid(self):
        """MAX_ITEM_QUANTITY — валидное значение (граница)."""
        item = self._add_item(
            self.cart, self.variant_a, quantity=MAX_ITEM_QUANTITY,
        )
        self.assertEqual(item.quantity, MAX_ITEM_QUANTITY)

    def test_quantity_1_boundary_valid(self):
        """1 — минимальное валидное значение (граница)."""
        item = self._add_item(self.cart, self.variant_a, quantity=1)
        self.assertEqual(item.quantity, 1)

    def test_unit_price_none_when_no_price(self):
        item = self._add_item(self.cart, self.variant_a)
        self.assertIsNone(item.unit_price)

    def test_total_price_none_when_no_price(self):
        item = self._add_item(self.cart, self.variant_a)
        self.assertIsNone(item.total_price)

    def test_unit_price_returns_price(self):
        """Если у варианта есть цена — unit_price возвращает её."""
        self._create_price(self.variant_a, price=Decimal('1500.00'))
        item = self._add_item(self.cart, self.variant_a)
        self.assertEqual(item.unit_price, Decimal('1500.00'))

    def test_total_price_calculation(self):
        """total_price = unit_price * quantity."""
        self._create_price(self.variant_a, price=Decimal('1500.00'))
        item = self._add_item(self.cart, self.variant_a, quantity=3)
        self.assertEqual(item.total_price, Decimal('4500.00'))

    def test_total_price_none_when_no_unit_price(self):
        """Без цены — total_price = None."""
        item = self._add_item(self.cart, self.variant_a, quantity=3)
        self.assertIsNone(item.total_price)

    def test_total_price_unsaved_item_no_crash(self):
        """Несохранённый OrderItem не падает с TypeError."""
        item = CartItem(cart=self.cart, variant=self.variant_a)
        # unit_price=None, quantity=None → total_price не должен падать
        total = item.total_price
        self.assertIsNone(total)

    def test_str_representation(self):
        item = self._add_item(self.cart, self.variant_a, quantity=5)
        self.assertIn('SKU-A', str(item))
        self.assertIn('5', str(item))

    def test_str_shows_times_symbol(self):
        """__str__ содержит символ × (умножение)."""
        item = self._add_item(self.cart, self.variant_a, quantity=1)
        self.assertIn('×', str(item))

    def test_cascade_delete_cart_deletes_items(self):
        self._add_item(self.cart, self.variant_a)
        self._add_item(self.cart, self.variant_b)
        self.cart.delete()
        self.assertEqual(CartItem.objects.count(), 0)

    def test_protect_variant(self):
        """variant on_delete=PROTECT — нельзя удалить вариант с CartItem."""
        self._add_item(self.cart, self.variant_a)
        with self.assertRaises(IntegrityError):
            self.variant_a.delete()

    def test_ordering(self):
        self.assertEqual(CartItem._meta.ordering, ('-created_at',))
