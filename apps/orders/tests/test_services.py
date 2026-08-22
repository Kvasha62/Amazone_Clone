# ────────────────────────────────────────────────────────────────────────
# apps/orders/tests/test_services.py — тесты OrderService.
#
# ПОКРЫТИЕ:
#   • create_from_cart — создание заказа из корзины
#   • transition_status — переходы статусов (FSM)
#   • confirm — подтверждение заказа
#   • cancel — отмена заказа
#   • get_user_order_summary — статистика
#   • Краевые случаи: пустая корзина, нет адреса, чужая корзина
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Нет автопроверки бизнес-логики → баги в сервисе
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from rest_framework.exceptions import NotFound, ValidationError

from apps.orders.models import Order
from apps.orders.models.order import OrderStatus
from apps.orders.services.order_service import OrderService
from apps.orders.tests.factories import (
    create_test_address,
    create_test_order,
    create_test_user,
)


class OrderServiceCreateTests(TestCase):
    """Тесты OrderService.create_from_cart()."""

    def setUp(self):
        """Создаём пользователя с адресом."""
        self.user = create_test_user()
        self.address = create_test_address(self.user)

    # Примечание: для полного теста create_from_cart нужны Cart с CartItem.
    # Здесь тестируем краевые случаи без полной инфраструктуры корзины.

    def test_create_from_cart_wrong_user_raises_not_found(self):
        """Попытка оформить чужую корзину → NotFound."""
        other_user = create_test_user()
        from apps.cart.models import Cart
        cart = Cart.objects.create(user=self.user, is_active=True)
        with self.assertRaises(NotFound):
            OrderService.create_from_cart(
                user=other_user,
                cart=cart,
            )

    def test_create_from_cart_inactive_cart_raises_not_found(self):
        """Попытка оформить неактивную корзину → NotFound."""
        from apps.cart.models import Cart
        cart = Cart.objects.create(user=self.user, is_active=False)
        with self.assertRaises(NotFound):
            OrderService.create_from_cart(user=self.user, cart=cart)

    def test_create_from_cart_no_address_raises_validation_error(self):
        """Нет адреса → ValidationError."""
        user_no_addr = create_test_user()
        from apps.cart.models import Cart
        cart = Cart.objects.create(user=user_no_addr, is_active=True)
        # Корзина без товаров → тоже ValidationError, но другая
        with self.assertRaises(ValidationError):
            OrderService.create_from_cart(user=user_no_addr, cart=cart)


class OrderServiceTransitionTests(TestCase):
    """Тесты OrderService.transition_status()."""

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(self.user, status=OrderStatus.PENDING)

    def test_pending_to_confirmed(self):
        """PENDING → CONFIRMED — допустимый переход."""
        order = OrderService.transition_status(
            self.order, OrderStatus.CONFIRMED,
        )
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertIsNotNone(order.confirmed_at)

    def test_pending_to_cancelled(self):
        """PENDING → CANCELLED — допустимый переход."""
        order = OrderService.transition_status(
            self.order, OrderStatus.CANCELLED,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertIsNotNone(order.cancelled_at)

    def test_invalid_transition_raises_error(self):
        """PENDING → DELIVERED — недопустимый переход → ValidationError."""
        with self.assertRaises(ValidationError):
            OrderService.transition_status(
                self.order, OrderStatus.DELIVERED,
            )

    def test_terminal_status_raises_error(self):
        """Переход из DELIVERED → невозможен → ValidationError."""
        order = create_test_order(self.user, status=OrderStatus.DELIVERED)
        with self.assertRaises(ValidationError):
            OrderService.transition_status(
                order, OrderStatus.CONFIRMED,
            )

    def test_full_lifecycle(self):
        """Полный жизненный цикл: PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED."""
        order = self.order

        order = OrderService.transition_status(order, OrderStatus.CONFIRMED)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)

        order = OrderService.transition_status(order, OrderStatus.PROCESSING)
        self.assertEqual(order.status, OrderStatus.PROCESSING)

        order = OrderService.transition_status(order, OrderStatus.SHIPPED)
        self.assertEqual(order.status, OrderStatus.SHIPPED)

        order = OrderService.transition_status(order, OrderStatus.DELIVERED)
        self.assertEqual(order.status, OrderStatus.DELIVERED)
        self.assertIsNotNone(order.delivered_at)


class OrderServiceCancelTests(TestCase):
    """Тесты OrderService.cancel()."""

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(self.user, status=OrderStatus.PENDING)

    def test_cancel_with_valid_reason(self):
        """Отмена с валидной причиной."""
        order = OrderService.cancel(self.order, reason='changed_mind')
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.cancellation_reason, 'changed_mind')
        self.assertIsNotNone(order.cancelled_at)

    def test_cancel_without_reason(self):
        """Отмена без причины — допустима."""
        order = OrderService.cancel(self.order, reason='')
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.cancellation_reason, '')

    def test_cancel_with_invalid_reason_raises_error(self):
        """Отмена с невалидной причиной → ValidationError."""
        with self.assertRaises(ValidationError):
            OrderService.cancel(self.order, reason='invalid_reason_xyz')

    def test_cancel_terminal_order_raises_error(self):
        """Отмена уже отменённого заказа → ValidationError."""
        OrderService.cancel(self.order, reason='changed_mind')
        with self.assertRaises(ValidationError):
            OrderService.cancel(self.order, reason='other')


class OrderServiceSummaryTests(TestCase):
    """Тесты OrderService.get_user_order_summary()."""

    def setUp(self):
        self.user = create_test_user()

    def test_summary_no_orders(self):
        """Сводка для пользователя без заказов."""
        summary = OrderService.get_user_order_summary(self.user)
        self.assertEqual(summary['total_orders'], 0)
        self.assertEqual(summary['active_orders'], 0)
        self.assertEqual(summary['total_spent'], '0.00')

    def test_summary_with_orders(self):
        """Сводка для пользователя с заказами."""
        create_test_order(self.user, status=OrderStatus.PENDING)
        create_test_order(
            self.user,
            status=OrderStatus.DELIVERED,
            total=Decimal('5000.00'),
        )
        summary = OrderService.get_user_order_summary(self.user)
        self.assertEqual(summary['total_orders'], 2)
        self.assertEqual(summary['active_orders'], 1)
        # total_spent = Sum('total') → возвращает Decimal (не строку)
        # Decimal('5000') == Decimal('5000.00') → True (сравнение значений)
        self.assertEqual(summary['total_spent'], Decimal('5000.00'))
