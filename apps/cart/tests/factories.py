"""
Фикстуры и утилиты для тестов корзины.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from apps.cart.constants import MAX_CART_ITEMS, MAX_ITEM_QUANTITY
from apps.cart.models import Cart, CartItem
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductVariant,
)
from apps.catalog.constants import ProductStatus

User = get_user_model()

# Сентинел: отличие «не передан user» от «передан user=None» (гость)
_UNSET = object()


class MockSession:
    """
    Лёгкий mock сессии для unit-тестов CartService.

    Имитирует интерфейс django.contrib.sessions.backends.base.SessionBase,
    который используется в CartService.get_or_create_cart():
      - session_key — атрибут (property)
      - create() — устанавливает ключ, если он пуст
    """

    def __init__(self, session_key=None):
        self._session_key = session_key

    @property
    def session_key(self):
        return self._session_key

    def create(self):
        """Имитирует SessionBase.create() — генерирует ключ."""
        if not self._session_key:
            self._session_key = 'mock-created-session-key'


class CartTestCase(TestCase):
    """
    Базовый класс для тестов корзины.

    Создаёт:
      - 1 пользователь (buyer)
      - 1 бренд, 1 категория, 1 товар
      - 2 варианта товара (SKU-A, SKU-B)
      - 1 неактивный вариант (SKU-INACTIVE)
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
        )
        cls.brand = Brand.objects.create(name='TestBrand')
        cls.root_cat = Category.add_root(name='Каталог')
        cls.product = Product.objects.create(
            name='Test Product',
            brand=cls.brand,
            primary_category=cls.root_cat,
            status=ProductStatus.ACTIVE,
        )
        cls.variant_a = ProductVariant.objects.create(
            product=cls.product,
            sku='SKU-A',
            is_active=True,
        )
        cls.variant_b = ProductVariant.objects.create(
            product=cls.product,
            sku='SKU-B',
            is_active=True,
        )
        cls.variant_inactive = ProductVariant.objects.create(
            product=cls.product,
            sku='SKU-INACTIVE',
            is_active=False,
        )

    def _create_cart(self, *, user=_UNSET, session_key='test-session') -> Cart:
        """Создаёт корзину для пользователя или гостя."""
        if user is _UNSET:
            user = self.user
        if user:
            return Cart.objects.create(user=user, is_active=True)
        session_hash = Cart.hash_session_key(session_key)
        return Cart.objects.create(session_key_hash=session_hash, is_active=True)

    def _add_item(self, cart, variant, quantity=1) -> CartItem:
        """Добавляет позицию в корзину напрямую через ORM."""
        return CartItem.objects.create(
            cart=cart,
            variant=variant,
            quantity=quantity,
        )

    def _make_request(self, user=None, session_key='test-session'):
        """Создаёт тестовый запрос для авторизованного пользователя."""
        factory = RequestFactory()
        request = factory.get('/')
        if user is None:
            user = self.user
        request.user = user
        request.session = MockSession(session_key=session_key)
        return request

    def _make_guest_request(self, session_key='guest-session-key'):
        """Создаёт запрос гостя (неавторизованный пользователь)."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = type('AnonymousUser', (), {
            'is_authenticated': False,
            'pk': None,
        })()
        request.session = MockSession(session_key=session_key)
        return request

    def _create_stock(self, variant, quantity=100, reserved=0):
        """Создаёт запись Stock для варианта."""
        from apps.inventory.models import Stock
        return Stock.objects.create(
            variant=variant,
            quantity=quantity,
            reserved_quantity=reserved,
        )

    def _create_price(self, variant, price=Decimal('1000.00'), sale_price=None):
        """Создаёт запись Price для варианта."""
        from apps.pricing.models import Price
        return Price.objects.create(
            variant=variant,
            price=price,
            sale_price=sale_price,
        )
