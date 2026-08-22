"""
Тесты CartService — бизнес-логика корзины.

⚠️  ВАЖНО: PostgreSQL запрещает FOR UPDATE на nullable-стороне LEFT JOIN.
Все тесты работают с PostgreSQL, где select_for_update() совместим
только с INNER JOIN (обязательные FK). Обратные OneToOne (stock, price)
читаются отдельными запросами без FOR UPDATE.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.cart.constants import MAX_CART_ITEMS, MAX_ITEM_QUANTITY
from apps.cart.models import Cart, CartItem
from apps.cart.services.cart_service import CartService
from apps.cart.tests.factories import CartTestCase
from apps.catalog.models import Product, ProductVariant
from apps.catalog.constants import ProductStatus

from rest_framework.exceptions import NotFound, ValidationError

User = get_user_model()


# ==============================================================
# get_or_create_cart
# ==============================================================

class GetOrCreateCartTests(CartTestCase):

    def test_creates_cart_for_authenticated_user(self):
        request = self._make_request()
        cart = CartService.get_or_create_cart(request)
        self.assertEqual(cart.user, self.user)
        self.assertTrue(cart.is_active)

    def test_returns_existing_cart(self):
        existing = self._create_cart()
        request = self._make_request()
        cart = CartService.get_or_create_cart(request)
        self.assertEqual(cart.pk, existing.pk)

    def test_creates_cart_for_guest(self):
        request = self._make_guest_request('guest-123')
        cart = CartService.get_or_create_cart(request)
        self.assertIsNone(cart.user)
        self.assertTrue(cart.session_key_hash)

    def test_same_guest_gets_same_cart(self):
        request1 = self._make_guest_request('same-session')
        request2 = self._make_guest_request('same-session')
        cart1 = CartService.get_or_create_cart(request1)
        cart2 = CartService.get_or_create_cart(request2)
        self.assertEqual(cart1.pk, cart2.pk)

    def test_different_guests_get_different_carts(self):
        """Разные session_key → разные корзины."""
        request1 = self._make_guest_request('session-alpha')
        request2 = self._make_guest_request('session-beta')
        cart1 = CartService.get_or_create_cart(request1)
        cart2 = CartService.get_or_create_cart(request2)
        self.assertNotEqual(cart1.pk, cart2.pk)

    def test_guest_without_session_key_creates_one(self):
        """Если у гостя нет session_key — get_or_create_cart вызывает create()."""
        request = self._make_guest_request(session_key=None)
        cart = CartService.get_or_create_cart(request)
        self.assertIsNone(cart.user)
        self.assertTrue(cart.session_key_hash)


# ==============================================================
# add_item
# ==============================================================

class AddItemTests(CartTestCase):

    def setUp(self):
        self.cart = self._create_cart()

    def test_add_new_item(self):
        item = CartService.add_item(self.cart, self.variant_a.pk, 2)
        self.assertEqual(item.variant, self.variant_a)
        self.assertEqual(item.quantity, 2)

    def test_add_same_item_increments(self):
        CartService.add_item(self.cart, self.variant_a.pk, 2)
        item = CartService.add_item(self.cart, self.variant_a.pk, 3)
        self.assertEqual(item.quantity, 5)

    def test_add_reject_inactive_variant(self):
        with self.assertRaises(NotFound):
            CartService.add_item(self.cart, self.variant_inactive.pk, 1)

    def test_add_reject_nonexistent_variant(self):
        with self.assertRaises(NotFound):
            CartService.add_item(self.cart, 99999, 1)

    def test_add_reject_negative_quantity(self):
        """Отрицательное количество — ValidationError."""
        with self.assertRaises(ValidationError):
            CartService.add_item(self.cart, self.variant_a.pk, -1)

    def test_add_reject_zero_quantity(self):
        """Нулевое количество — ValidationError."""
        with self.assertRaises(ValidationError):
            CartService.add_item(self.cart, self.variant_a.pk, 0)

    def test_add_reject_archived_product(self):
        """Вариант активен, но товар ARCHIVED — NotFound."""
        archived_product = Product.objects.create(
            name='Archived Product',
            brand=self.brand,
            primary_category=self.root_cat,
            status=ProductStatus.ARCHIVED,
        )
        variant = ProductVariant.objects.create(
            product=archived_product,
            sku='SKU-ARCHIVED',
            is_active=True,
        )
        with self.assertRaises(NotFound):
            CartService.add_item(self.cart, variant.pk, 1)

    def test_add_reject_draft_product(self):
        """Вариант активен, но товар DRAFT — NotFound."""
        draft_product = Product.objects.create(
            name='Draft Product',
            brand=self.brand,
            primary_category=self.root_cat,
            status=ProductStatus.DRAFT,
        )
        variant = ProductVariant.objects.create(
            product=draft_product,
            sku='SKU-DRAFT',
            is_active=True,
        )
        with self.assertRaises(NotFound):
            CartService.add_item(self.cart, variant.pk, 1)

    def test_add_reject_exceeds_max_items(self):
        for i in range(MAX_CART_ITEMS):
            v = ProductVariant.objects.create(
                product=self.product,
                sku=f'SKU-MAX-{i}',
                is_active=True,
            )
            CartService.add_item(self.cart, v.pk, 1)

        v_extra = ProductVariant.objects.create(
            product=self.product,
            sku='SKU-EXTRA',
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            CartService.add_item(self.cart, v_extra.pk, 1)

    def test_add_quantity_boundary_max(self):
        """quantity=MAX_ITEM_QUANTITY — валидно."""
        item = CartService.add_item(
            self.cart, self.variant_a.pk, MAX_ITEM_QUANTITY,
        )
        self.assertEqual(item.quantity, MAX_ITEM_QUANTITY)

    # ── Тесты с Stock (PostgreSQL: stock через отдельный запрос) ──

    def test_add_with_sufficient_stock(self):
        """Достаточно на складе — добавление OK."""
        self._create_stock(self.variant_a, quantity=10)
        item = CartService.add_item(self.cart, self.variant_a.pk, 5)
        self.assertEqual(item.quantity, 5)

    def test_add_reject_exceeds_stock(self):
        """Запрошено больше чем на складе — ValidationError."""
        self._create_stock(self.variant_a, quantity=3)
        with self.assertRaises(ValidationError):
            CartService.add_item(self.cart, self.variant_a.pk, 5)

    def test_add_increment_respects_stock(self):
        """При увеличении количества — проверка stock."""
        self._create_stock(self.variant_a, quantity=5)
        CartService.add_item(self.cart, self.variant_a.pk, 3)
        # 3 в корзине + 3 хотим добавить = 6 > 5 на складе → ошибка
        with self.assertRaises(ValidationError):
            CartService.add_item(self.cart, self.variant_a.pk, 3)

    def test_add_no_stock_record_allows_any_quantity(self):
        """Нет записи Stock — нет ограничения (stock=None)."""
        item = CartService.add_item(self.cart, self.variant_a.pk, 999)
        self.assertEqual(item.quantity, 999)

    def test_add_with_stock_exact_quantity(self):
        """Запрошено ровно столько, сколько на складе — OK."""
        self._create_stock(self.variant_a, quantity=5)
        item = CartService.add_item(self.cart, self.variant_a.pk, 5)
        self.assertEqual(item.quantity, 5)


# ==============================================================
# update_item_quantity
# ==============================================================

class UpdateItemTests(CartTestCase):

    def setUp(self):
        self.cart = self._create_cart()
        self.item = self._add_item(self.cart, self.variant_a, 2)

    def test_update_quantity(self):
        item = CartService.update_item_quantity(
            self.cart, self.item.pk, 5,
        )
        self.assertEqual(item.quantity, 5)

    def test_update_reject_not_owned_item(self):
        other_user = User.objects.create_user(
            username='other', email='other@test.com', password='p',
        )
        other_cart = self._create_cart(user=other_user)
        with self.assertRaises(NotFound):
            CartService.update_item_quantity(other_cart, self.item.pk, 3)

    def test_update_reject_nonexistent_item(self):
        with self.assertRaises(NotFound):
            CartService.update_item_quantity(self.cart, 99999, 3)

    def test_update_persists_to_db(self):
        """Обновлённое количество сохраняется в БД."""
        CartService.update_item_quantity(self.cart, self.item.pk, 10)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 10)

    def test_update_to_quantity_1(self):
        """Минимальное валидное количество при обновлении."""
        item = CartService.update_item_quantity(self.cart, self.item.pk, 1)
        self.assertEqual(item.quantity, 1)

    def test_update_with_stock_limit(self):
        """Нельзя обновить количество больше чем stock."""
        self._create_stock(self.variant_a, quantity=3)
        with self.assertRaises(ValidationError):
            CartService.update_item_quantity(self.cart, self.item.pk, 5)

    def test_update_within_stock(self):
        """Обновление количества в пределах stock — OK."""
        self._create_stock(self.variant_a, quantity=10)
        item = CartService.update_item_quantity(self.cart, self.item.pk, 8)
        self.assertEqual(item.quantity, 8)

    def test_update_no_stock_allows_any_quantity(self):
        """Нет Stock — нет ограничения."""
        item = CartService.update_item_quantity(
            self.cart, self.item.pk, MAX_ITEM_QUANTITY,
        )
        self.assertEqual(item.quantity, MAX_ITEM_QUANTITY)


# ==============================================================
# remove_item
# ==============================================================

class RemoveItemTests(CartTestCase):

    def setUp(self):
        self.cart = self._create_cart()
        self.item = self._add_item(self.cart, self.variant_a, 1)

    def test_remove_item(self):
        CartService.remove_item(self.cart, self.item.pk)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_remove_reject_nonexistent(self):
        with self.assertRaises(NotFound):
            CartService.remove_item(self.cart, 99999)

    def test_remove_reject_not_owned(self):
        other_user = User.objects.create_user(
            username='other2', email='other2@test.com', password='p',
        )
        other_cart = self._create_cart(user=other_user)
        with self.assertRaises(NotFound):
            CartService.remove_item(other_cart, self.item.pk)

    def test_remove_twice_fails(self):
        """Повторное удаление того же item — NotFound."""
        CartService.remove_item(self.cart, self.item.pk)
        with self.assertRaises(NotFound):
            CartService.remove_item(self.cart, self.item.pk)


# ==============================================================
# clear
# ==============================================================

class ClearCartTests(CartTestCase):

    def test_clear_empties_cart(self):
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 2)
        self._add_item(cart, self.variant_b, 3)
        CartService.clear(cart)
        self.assertEqual(cart.items.count(), 0)

    def test_clear_empty_cart_ok(self):
        """Очистка уже пустой корзины — без ошибок."""
        cart = self._create_cart()
        CartService.clear(cart)
        self.assertEqual(cart.items.count(), 0)

    def test_clear_then_add(self):
        """После очистки можно снова добавить товар."""
        cart = self._create_cart()
        self._add_item(cart, self.variant_a, 2)
        CartService.clear(cart)
        item = CartService.add_item(cart, self.variant_b.pk, 1)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(cart.items.count(), 1)


# ==============================================================
# merge_guest_into_user_cart
# ==============================================================

class MergeCartTests(CartTestCase):

    def setUp(self):
        self.guest_cart = self._create_cart(
            user=None, session_key='merge-session',
        )
        self.user2 = User.objects.create_user(
            username='buyer2', email='buyer2@test.com', password='p',
        )

    def test_merge_guest_into_user(self):
        self._add_item(self.guest_cart, self.variant_a, 2)
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        items = user_cart.items.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity, 2)

    def test_merge_deactivates_guest_cart(self):
        self._add_item(self.guest_cart, self.variant_a, 1)
        CartService.merge_guest_into_user_cart('merge-session', self.user2)
        self.guest_cart.refresh_from_db()
        self.assertFalse(self.guest_cart.is_active)

    def test_merge_returns_none_if_no_guest(self):
        result = CartService.merge_guest_into_user_cart(
            'nonexistent-session', self.user2,
        )
        self.assertIsNone(result)

    def test_merge_skips_inactive_variants(self):
        self._add_item(self.guest_cart, self.variant_inactive, 3)
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        self.assertEqual(user_cart.items.count(), 0)

    def test_merge_sums_quantities_if_existing(self):
        self._add_item(self.guest_cart, self.variant_a, 2)
        user_cart = Cart.objects.create(user=self.user2, is_active=True)
        CartItem.objects.create(
            cart=user_cart, variant=self.variant_a, quantity=3,
        )
        result = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        item = CartItem.objects.get(cart=result, variant=self.variant_a)
        self.assertEqual(item.quantity, 5)

    def test_merge_multiple_items(self):
        self._add_item(self.guest_cart, self.variant_a, 1)
        self._add_item(self.guest_cart, self.variant_b, 2)
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        self.assertEqual(user_cart.items.count(), 2)

    def test_merge_skips_archived_product(self):
        """Вариант активен, но товар ARCHIVED — пропускается при merge."""
        archived_product = Product.objects.create(
            name='Archived Merge Product',
            brand=self.brand,
            primary_category=self.root_cat,
            status=ProductStatus.ARCHIVED,
        )
        variant = ProductVariant.objects.create(
            product=archived_product,
            sku='SKU-MERGE-ARCHIVED',
            is_active=True,
        )
        self._add_item(self.guest_cart, variant, 3)
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        self.assertEqual(user_cart.items.count(), 0)

    def test_merge_idempotent(self):
        """Повторный merge после деактивации — None (нет гостевой)."""
        self._add_item(self.guest_cart, self.variant_a, 1)
        CartService.merge_guest_into_user_cart('merge-session', self.user2)
        result = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        self.assertIsNone(result)

    def test_merge_creates_user_cart_if_none(self):
        """Если у пользователя ещё нет корзины — merge создаёт её."""
        self._add_item(self.guest_cart, self.variant_a, 1)
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        self.assertEqual(user_cart.user, self.user2)
        self.assertTrue(user_cart.is_active)

    def test_merge_with_stock_limits_quantity(self):
        """Stock ограничивает количество при merge."""
        self._create_stock(self.variant_a, quantity=3)
        self._add_item(self.guest_cart, self.variant_a, 5)
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        item = CartItem.objects.get(cart=user_cart, variant=self.variant_a)
        self.assertEqual(item.quantity, 3)  # min(5, stock=3)

    def test_merge_empty_guest_cart(self):
        """Пустая гостевая корзина — merge деактивирует её, юзерская пуста."""
        user_cart = CartService.merge_guest_into_user_cart(
            'merge-session', self.user2,
        )
        self.guest_cart.refresh_from_db()
        self.assertFalse(self.guest_cart.is_active)
        self.assertEqual(user_cart.items.count(), 0)
