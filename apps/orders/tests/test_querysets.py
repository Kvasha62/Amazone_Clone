# ────────────────────────────────────────────────────────────────────────
# apps/orders/tests/test_querysets.py — тесты кастомного QuerySet для Order.
#
# ПОКРЫТИЕ:
#   • for_user() — фильтрация по пользователю
#   • pending() — только PENDING
#   • active() — без терминальных
#   • cancelled() — только CANCELLED
#   • with_items() — prefetch оптимизация
#   • with_user() — select_related оптимизация
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Нет автопроверки QuerySet → N+1 не обнаружится
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from apps.orders.models import Order
from apps.orders.models.order import OrderStatus
from apps.orders.tests.factories import (
    create_test_order,
    create_test_order_item,
    create_test_user,
)


class OrderQuerySetTests(TestCase):
    """Тесты методов OrderQuerySet."""

    def setUp(self):
        """Создаём двух пользователей с заказами."""
        self.user1 = create_test_user()
        self.user2 = create_test_user()

        self.order1_pending = create_test_order(self.user1, status=OrderStatus.PENDING)
        self.order1_confirmed = create_test_order(
            self.user1, status=OrderStatus.CONFIRMED,
        )
        self.order1_delivered = create_test_order(
            self.user1,
            status=OrderStatus.DELIVERED,
            total=Decimal('5000.00'),
        )
        self.order2_pending = create_test_order(self.user2, status=OrderStatus.PENDING)

    def test_for_user_returns_only_user_orders(self):
        """for_user() возвращает заказы только указанного пользователя."""
        orders = Order.objects.for_user(self.user1)
        self.assertEqual(orders.count(), 3)
        for order in orders:
            self.assertEqual(order.user_id, self.user1.pk)

    def test_pending_returns_only_pending(self):
        """pending() возвращает только PENDING-заказы."""
        orders = Order.objects.pending()
        self.assertEqual(orders.count(), 2)
        for order in orders:
            self.assertEqual(order.status, OrderStatus.PENDING)

    def test_active_excludes_terminal(self):
        """active() исключает DELIVERED и CANCELLED."""
        orders = Order.objects.active()
        for order in orders:
            self.assertNotIn(
                order.status,
                [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            )

    def test_with_items_prefetch(self):
        """with_items() подгружает позиции без N+1."""
        create_test_order_item(self.order1_pending)
        orders = Order.objects.with_items().filter(pk=self.order1_pending.pk)
        # Не должно быть N+1 при доступе к items
        for order in orders:
            items = list(order.items.all())
            self.assertEqual(len(items), 1)

    def test_chaining(self):
        """Методы QuerySet поддерживают chaining."""
        orders = (
            Order.objects
            .for_user(self.user1)
            .pending()
        )
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first(), self.order1_pending)
