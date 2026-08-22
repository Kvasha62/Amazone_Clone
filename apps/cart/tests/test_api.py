"""
Тесты API endpoints корзины.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.cart.tests.factories import CartTestCase

User = get_user_model()


class CartAPITestCase(CartTestCase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)


# ==========================================================
# GET /api/v1/cart/
# ==========================================================

class CartGetTests(CartAPITestCase):

    def test_get_cart_empty(self):
        resp = self.client.get('/api/v1/cart/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items'], [])
        self.assertEqual(resp.data['total_quantity'], 0)

    def test_get_cart_with_items(self):
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 2)
        resp = self.client.get('/api/v1/cart/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['items']), 1)
        self.assertEqual(resp.data['items'][0]['quantity'], 2)

    def test_get_cart_total_quantity(self):
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 2)
        self._add_item(cart, self.variant_b, 3)
        resp = self.client.get('/api/v1/cart/')
        self.assertEqual(resp.data['total_quantity'], 5)

    def test_get_cart_total_is_decimal(self):
        """total для пустой корзины — Decimal('0.00')."""
        resp = self.client.get('/api/v1/cart/')
        self.assertEqual(resp.data['total'], Decimal('0.00'))

    def test_get_cart_unauthenticated(self):
        self.client.logout()
        resp = self.client.get('/api/v1/cart/')
        # AllowAny — создаёт гостевую корзину
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_get_cart_returns_cart_id(self):
        """Ответ содержит id корзины."""
        resp = self.client.get('/api/v1/cart/')
        self.assertIn('id', resp.data)

    def test_get_cart_item_fields(self):
        """CartItem в ответе содержит все нужные поля."""
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 1)
        resp = self.client.get('/api/v1/cart/')
        item = resp.data['items'][0]
        expected_fields = {
            'id', 'product_name', 'sku', 'price', 'quantity', 'total_price',
        }
        self.assertEqual(set(item.keys()), expected_fields)

    def test_get_cart_item_shows_product_name(self):
        """product_name содержит имя товара."""
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 1)
        resp = self.client.get('/api/v1/cart/')
        self.assertEqual(resp.data['items'][0]['product_name'], 'Test Product')


# ==========================================================
# DELETE /api/v1/cart/
# ==========================================================

class CartClearTests(CartAPITestCase):

    def test_clear_cart(self):
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 2)
        resp = self.client.delete('/api/v1/cart/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items'], [])

    def test_clear_already_empty(self):
        resp = self.client.delete('/api/v1/cart/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_clear_then_add(self):
        """После очистки можно снова добавить товар."""
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 2)
        self.client.delete('/api/v1/cart/')
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_b.pk,
            'quantity': 1,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data['items']), 1)


# ==========================================================
# POST /api/v1/cart/items/
# ==========================================================

class CartAddItemTests(CartAPITestCase):

    def test_add_item(self):
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 2,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data['items']), 1)
        self.assertEqual(resp.data['items'][0]['quantity'], 2)

    def test_add_item_default_quantity(self):
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['items'][0]['quantity'], 1)

    def test_add_same_item_increments(self):
        self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 2,
        }, format='json')
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 3,
        }, format='json')
        self.assertEqual(resp.data['items'][0]['quantity'], 5)

    def test_add_inactive_variant_404(self):
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_inactive.pk,
            'quantity': 1,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_invalid_quantity(self):
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 0,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_missing_variant_id(self):
        resp = self.client.post('/api/v1/cart/items/', {
            'quantity': 1,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_negative_quantity(self):
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': -5,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_string_quantity(self):
        """quantity=строка → 400."""
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 'abc',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_creates_cart_automatically(self):
        """Если корзины нет — она создаётся при добавлении."""
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 1,
        }, format='json')
        self.assertTrue(
            Cart.objects.filter(user=self.user, is_active=True).exists(),
        )

    def test_add_with_stock_limit(self):
        """Превышение stock → 400."""
        self._create_stock(self.variant_a, quantity=2)
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 5,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# PATCH /api/v1/cart/items/<id>/
# ==========================================================

class CartUpdateItemTests(CartAPITestCase):

    def setUp(self):
        super().setUp()
        self.cart = self._create_cart()
        self.item = self._add_item(self.cart, self.variant_a, 2)

    def test_update_quantity(self):
        resp = self.client.patch(
            f'/api/v1/cart/items/{self.item.pk}/',
            {'quantity': 5},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items'][0]['quantity'], 5)

    def test_update_invalid_quantity(self):
        resp = self.client.patch(
            f'/api/v1/cart/items/{self.item.pk}/',
            {'quantity': 0},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_not_owned_item(self):
        other_user = User.objects.create_user(
            username='other', email='other@test.com', password='p',
        )
        other_cart = Cart.objects.create(user=other_user, is_active=True)
        other_item = CartItem.objects.create(
            cart=other_cart, variant=self.variant_a, quantity=1,
        )
        resp = self.client.patch(
            f'/api/v1/cart/items/{other_item.pk}/',
            {'quantity': 5},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_missing_body(self):
        """PATCH без body → 400."""
        resp = self.client.patch(
            f'/api/v1/cart/items/{self.item.pk}/',
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# DELETE /api/v1/cart/items/<id>/
# ==========================================================

class CartRemoveItemTests(CartAPITestCase):

    def setUp(self):
        super().setUp()
        self.cart = self._create_cart()
        self.item = self._add_item(self.cart, self.variant_a, 2)

    def test_remove_item(self):
        resp = self.client.delete(
            f'/api/v1/cart/items/{self.item.pk}/',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items'], [])

    def test_remove_nonexistent_item(self):
        resp = self.client.delete('/api/v1/cart/items/99999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_not_owned_item(self):
        other_user = User.objects.create_user(
            username='other2', email='other2@test.com', password='p',
        )
        other_cart = Cart.objects.create(user=other_user, is_active=True)
        other_item = CartItem.objects.create(
            cart=other_cart, variant=self.variant_a, quantity=1,
        )
        resp = self.client.delete(
            f'/api/v1/cart/items/{other_item.pk}/',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_then_re_add(self):
        """Удалили и добавили снова — 1 позиция с новым quantity."""
        self.client.delete(f'/api/v1/cart/items/{self.item.pk}/')
        resp = self.client.post('/api/v1/cart/items/', {
            'variant_id': self.variant_a.pk,
            'quantity': 10,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['items'][0]['quantity'], 10)


# ==========================================================
# POST /api/v1/cart/merge/
# ==========================================================

class CartMergeAPITests(CartAPITestCase):

    def test_merge_requires_auth(self):
        self.client.logout()
        resp = self.client.post('/api/v1/cart/merge/')
        self.assertIn(resp.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_merge_no_guest_session(self):
        """Авторизован, но нет session_key — 400."""
        resp = self.client.post('/api/v1/cart/merge/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
