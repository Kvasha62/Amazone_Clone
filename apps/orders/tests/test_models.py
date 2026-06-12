# ────────────────────────────────────────────────────────────────────────
# apps/orders/tests/test_models.py — тесты моделей Order и OrderItem.
#
# ПОКРЫТИЕ:
#   • Создание заказа с defaults
#   • UniqueConstraint на order_number
#   • CheckConstraints (total ≥ 0, quantity range, unit_price)
#   • Property: is_terminal, full_address, total_price
#   • recalculate_total()
#   • __str__() — строковое представление
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.TestCase
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Нет автопроверки моделей → баги в constraints не обнаружатся
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.orders.models import Order, OrderItem
from apps.orders.models.order import OrderStatus
from apps.orders.tests.factories import (
    create_test_order,
    create_test_order_item,
    create_test_user,
)


class OrderModelTests(TestCase):
    """Тесты модели Order."""

    def setUp(self):
        """Создаём тестовые данные для каждого теста."""
        self.user = create_test_user()
        self.order = create_test_order(self.user)

    # ── Создание ──

    def test_create_order_generates_order_number(self):
        """При создании заказа автоматически генерируется order_number."""
        self.assertTrue(self.order.order_number.startswith('ORD-'))
        # Формат: ORD-{6 цифр}
        parts = self.order.order_number.split('-')
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[1].isdigit())

    def test_order_default_status_is_pending(self):
        """Статус по умолчанию — PENDING."""
        self.assertEqual(self.order.status, OrderStatus.PENDING)

    def test_order_number_is_unique(self):
        """Два заказа не могут иметь одинаковый order_number."""
        order2 = create_test_order(self.user)
        self.assertNotEqual(self.order.order_number, order2.order_number)

    # ── Constraints ──

    def test_order_total_cannot_be_negative(self):
        """CheckConstraint: total ≥ 0."""
        with self.assertRaises(IntegrityError):
            create_test_order(
                self.user,
                total=Decimal('-100.00'),
                subtotal=Decimal('-100.00'),
            )

    def test_order_subtotal_cannot_be_negative(self):
        """CheckConstraint: subtotal ≥ 0."""
        with self.assertRaises(IntegrityError):
            create_test_order(
                self.user,
                subtotal=Decimal('-50.00'),
            )

    # ── Properties ──

    def test_is_terminal_for_delivered(self):
        """DELIVERED — терминальный статус."""
        self.order.status = OrderStatus.DELIVERED
        self.assertTrue(self.order.is_terminal)

    def test_is_terminal_for_cancelled(self):
        """CANCELLED — терминальный статус."""
        self.order.status = OrderStatus.CANCELLED
        self.assertTrue(self.order.is_terminal)

    def test_is_not_terminal_for_pending(self):
        """PENDING — не терминальный статус."""
        self.assertFalse(self.order.is_terminal)

    def test_is_not_terminal_for_confirmed(self):
        """CONFIRMED — не терминальный статус."""
        self.order.status = OrderStatus.CONFIRMED
        self.assertFalse(self.order.is_terminal)

    def test_full_address_with_all_fields(self):
        """Полный адрес включает все заполненные поля."""
        self.order.country = 'Россия'
        self.order.region = 'Московская область'
        self.order.city = 'Москва'
        self.order.street = 'ул. Тестовая, д. 1'
        self.order.postal_code = '123456'
        expected = 'Россия, Московская область, Москва, ул. Тестовая, д. 1 (123456)'
        self.assertEqual(self.order.full_address, expected)

    def test_full_address_without_region_and_postal(self):
        """Полный адрес без региона и индекса."""
        self.order.region = ''
        self.order.postal_code = ''
        expected = 'Россия, Москва, ул. Тестовая, д. 1'
        self.assertEqual(self.order.full_address, expected)

    # ── __str__ ──

    def test_str_representation(self):
        """__str__ содержит номер заказа и статус."""
        order_str = str(self.order)
        self.assertIn(self.order.order_number, order_str)
        self.assertIn('Ожидает оплаты', order_str)

    # ── recalculate_total ──

    def test_recalculate_total(self):
        """recalculate_total корректно пересчитывает сумму."""
        create_test_order_item(
            self.order,
            unit_price=Decimal('1000.00'),
            quantity=2,
        )
        create_test_order_item(
            self.order,
            unit_price=Decimal('500.00'),
            quantity=1,
            sku='TEST-SKU-2',
        )
        self.order.recalculate_total()
        # subtotal = 1000×2 + 500×1 = 2500
        self.assertEqual(self.order.subtotal, Decimal('2500.00'))
        # total = 2500 + 0 - 0 = 2500
        self.assertEqual(self.order.total, Decimal('2500.00'))


class OrderItemModelTests(TestCase):
    """Тесты модели OrderItem."""

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(self.user)

    def test_create_order_item(self):
        """Создание позиции заказа."""
        item = create_test_order_item(self.order)
        self.assertEqual(item.order, self.order)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.unit_price, Decimal('1000.00'))

    def test_total_price_property(self):
        """total_price = unit_price × quantity."""
        item = create_test_order_item(
            self.order,
            unit_price=Decimal('899.00'),
            quantity=3,
        )
        self.assertEqual(item.total_price, Decimal('2697.00'))

    def test_quantity_cannot_be_zero(self):
        """CheckConstraint: quantity ≥ 1."""
        with self.assertRaises(IntegrityError):
            create_test_order_item(self.order, quantity=0)

    def test_quantity_cannot_exceed_max(self):
        """CheckConstraint: quantity ≤ 999."""
        from apps.orders.constants import MAX_ITEM_QUANTITY
        with self.assertRaises(IntegrityError):
            create_test_order_item(self.order, quantity=MAX_ITEM_QUANTITY + 1)

    def test_unit_price_cannot_be_zero(self):
        """CheckConstraint: unit_price ≥ 0.01."""
        with self.assertRaises(IntegrityError):
            create_test_order_item(self.order, unit_price=Decimal('0.00'))

    def test_unique_order_sku(self):
        """UniqueConstraint: уникальная пара (order, sku)."""
        create_test_order_item(self.order, sku='SKU-A')
        with self.assertRaises(IntegrityError):
            create_test_order_item(self.order, sku='SKU-A')

    def test_str_representation(self):
        """__str__ содержит название, SKU, количество и цену."""
        item = create_test_order_item(self.order)
        item_str = str(item)
        self.assertIn('Тестовый товар', item_str)
        self.assertIn('@ 1000.00', item_str)
