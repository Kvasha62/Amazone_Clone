# ────────────────────────────────────────────────────────────────────────
# apps/payments/tests/test_inventory_integration.py — интеграционные тесты
# связи платежей, заказов и склада.
#
# ПРОВЕРЯЕТ:
#   • confirm_payment → OrderService.confirm → InventoryService.reserve_stock
#   • Отмена заказа → InventoryService.release_stock
#   • Доставка → InventoryService.commit_stock
#   • Создание заказа с реальными OrderItem + Stock
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from apps.catalog.tests.factories import CatalogTestCase
from apps.inventory.models import Stock, StockMovement
from apps.inventory.services.inventory_service import InventoryService
from apps.orders.models.order import OrderStatus
from apps.orders.services.order_service import OrderService
from apps.orders.tests.factories import create_test_user
from apps.payments.services.payment_service import PaymentService


class InventoryOrderIntegrationTests(CatalogTestCase):
    """
    Интеграционные тесты: Order ↔ Inventory ↔ Payment.

    Использует CatalogTestCase для создания товаров и вариантов
    с реальными ценами (variant_128, variant_256).
    """

    def setUp(self):
        self.user = create_test_user()
        # Создаём адрес для пользователя
        from apps.users.models import Address
        Address.objects.create(
            user=self.user,
            recipient_name='Тест Тестов',
            country='Россия',
            city='Москва',
            street='ул. Тестовая, д. 1',
            postal_code='123456',
            is_default=True,
        )
        # Создаём сток для вариантов
        InventoryService.restock(self.variant_128, 100)
        InventoryService.restock(self.variant_256, 50)

    def _create_order_from_cart(self):
        """Вспомогательный метод: создаёт заказ из корзины с товарами."""
        from apps.cart.models import Cart, CartItem
        from apps.cart.services.cart_service import CartService
        from apps.pricing.models import Price

        # Создаём цены для вариантов (если ещё нет)
        try:
            self.variant_128.refresh_from_db()
            self.variant_128.price
        except Exception:
            Price.objects.create(
                variant=self.variant_128,
                price=Decimal('89990.00'),
            )
        try:
            self.variant_256.refresh_from_db()
            self.variant_256.price
        except Exception:
            Price.objects.create(
                variant=self.variant_256,
                price=Decimal('99990.00'),
            )

        cart = Cart.objects.create(user=self.user, is_active=True)
        CartItem.objects.create(
            cart=cart, variant=self.variant_128, quantity=3,
        )
        CartItem.objects.create(
            cart=cart, variant=self.variant_256, quantity=2,
        )

        order = OrderService.create_from_cart(
            user=self.user,
            cart=cart,
        )
        return order

    # ── Резервирование при CONFIRMED ──

    def test_confirm_order_reserves_stock(self):
        """Подтверждение заказа резервирует сток."""
        order = self._create_order_from_cart()

        # Подтверждаем заказ
        OrderService.transition_status(order, OrderStatus.CONFIRMED)

        # Проверяем что сток зарезервирован
        stock_128 = Stock.objects.get(variant=self.variant_128)
        stock_256 = Stock.objects.get(variant=self.variant_256)

        self.assertEqual(stock_128.reserved_quantity, 3)
        self.assertEqual(stock_256.reserved_quantity, 2)
        # Физический остаток не изменился
        self.assertEqual(stock_128.quantity, 100)
        self.assertEqual(stock_256.quantity, 50)

    def test_confirm_creates_reserve_movements(self):
        """Подтверждение создаёт StockMovement(RESERVE)."""
        order = self._create_order_from_cart()
        OrderService.transition_status(order, OrderStatus.CONFIRMED)

        movements = StockMovement.objects.filter(
            order=order,
            kind='reserve',
        )
        self.assertEqual(movements.count(), 2)

    # ── Освобождение при CANCELLED ──

    def test_cancel_order_releases_stock(self):
        """Отмена заказа освобождает зарезервированный сток."""
        order = self._create_order_from_cart()
        OrderService.transition_status(order, OrderStatus.CONFIRMED)

        # Отменяем заказ
        OrderService.cancel(order, reason='changed_mind')

        # Проверяем что резерв снят
        stock_128 = Stock.objects.get(variant=self.variant_128)
        stock_256 = Stock.objects.get(variant=self.variant_256)

        self.assertEqual(stock_128.reserved_quantity, 0)
        self.assertEqual(stock_256.reserved_quantity, 0)
        # Физический остаток не изменился
        self.assertEqual(stock_128.quantity, 100)
        self.assertEqual(stock_256.quantity, 50)

    def test_cancel_creates_release_movements(self):
        """Отмена создаёт StockMovement(RELEASE)."""
        order = self._create_order_from_cart()
        OrderService.transition_status(order, OrderStatus.CONFIRMED)
        OrderService.cancel(order, reason='other')

        movements = StockMovement.objects.filter(
            order=order,
            kind='release',
        )
        self.assertEqual(movements.count(), 2)

    # ── Списание при DELIVERED ──

    def test_delivered_commits_stock(self):
        """Доставка списывает физический сток и снимает резерв."""
        order = self._create_order_from_cart()

        # Полный путь: PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED
        OrderService.transition_status(order, OrderStatus.CONFIRMED)
        OrderService.transition_status(order, OrderStatus.PROCESSING)
        OrderService.transition_status(order, OrderStatus.SHIPPED)
        OrderService.transition_status(order, OrderStatus.DELIVERED)

        # Проверяем что сток списан
        stock_128 = Stock.objects.get(variant=self.variant_128)
        stock_256 = Stock.objects.get(variant=self.variant_256)

        self.assertEqual(stock_128.quantity, 97)   # 100 - 3
        self.assertEqual(stock_128.reserved_quantity, 0)  # резерв снят
        self.assertEqual(stock_256.quantity, 48)   # 50 - 2
        self.assertEqual(stock_256.reserved_quantity, 0)

    def test_delivered_creates_out_movements(self):
        """Доставка создаёт StockMovement(OUT)."""
        order = self._create_order_from_cart()
        OrderService.transition_status(order, OrderStatus.CONFIRMED)
        OrderService.transition_status(order, OrderStatus.PROCESSING)
        OrderService.transition_status(order, OrderStatus.SHIPPED)
        OrderService.transition_status(order, OrderStatus.DELIVERED)

        movements = StockMovement.objects.filter(
            order=order,
            kind='out',
        )
        self.assertEqual(movements.count(), 2)

    # ── Полный цикл: Payment → Confirm → Deliver ──

    def test_payment_confirm_reserves_and_deliver_commits(self):
        """Полный цикл: оплата → резерв → сборка → отправка → доставка."""
        order = self._create_order_from_cart()

        # Оплата через PaymentService
        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
            amount=order.total,
        )
        PaymentService.process_payment(payment)
        PaymentService.confirm_payment(payment)

        # Проверяем: заказ подтверждён, сток зарезервирован
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMED)

        stock_128 = Stock.objects.get(variant=self.variant_128)
        self.assertEqual(stock_128.reserved_quantity, 3)

        # Доставляем
        OrderService.transition_status(order, OrderStatus.PROCESSING)
        OrderService.transition_status(order, OrderStatus.SHIPPED)
        OrderService.transition_status(order, OrderStatus.DELIVERED)

        # Проверяем: сток списан
        stock_128.refresh_from_db()
        self.assertEqual(stock_128.quantity, 97)
        self.assertEqual(stock_128.reserved_quantity, 0)

    # ── Краевой случай: заказ без OrderItem ──

    def test_confirm_order_without_items_no_error(self):
        """Подтверждение заказа без OrderItem не падает."""
        from apps.orders.tests.factories import create_test_order
        order = create_test_order(self.user, status=OrderStatus.PENDING)

        # Не должно падать — graceful handling
        result = OrderService.transition_status(order, OrderStatus.CONFIRMED)
        self.assertEqual(result.status, OrderStatus.CONFIRMED)

    def test_cancel_order_without_items_no_error(self):
        """Отмена заказа без OrderItem не падает."""
        from apps.orders.tests.factories import create_test_order
        order = create_test_order(self.user, status=OrderStatus.PENDING)

        result = OrderService.cancel(order, reason='other')
        self.assertEqual(result.status, OrderStatus.CANCELLED)
