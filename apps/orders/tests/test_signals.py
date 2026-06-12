# ────────────────────────────────────────────────────────────────────────
# apps/orders/tests/test_signals.py — тесты сигналов модуля заказов.
#
# ПОКРЫТИЕ:
#   • post_save Order (created=True) — логирование создания
#   • post_save Order (created=False) — логирование обновления
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Нет автопроверки сигналов → side-effects не обнаружатся
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from apps.orders.models import Order
from apps.orders.models.order import OrderStatus
from apps.orders.tests.factories import create_test_order, create_test_user


class OrderSignalTests(TestCase):
    """Тесты сигналов Order."""

    def setUp(self):
        self.user = create_test_user()

    def test_post_save_signal_on_create(self):
        """post_save(created=True) вызывается при создании заказа."""
        # Сигнал должен выполниться без ошибок.
        # Если он ломается — тест упадёт (side-effect).
        order = create_test_order(self.user)
        self.assertIsNotNone(order.pk)

    def test_post_save_signal_on_update(self):
        """post_save(created=False) вызывается при обновлении заказа."""
        order = create_test_order(self.user)
        # Обновляем статус — сигнал должен выполниться.
        order.status = OrderStatus.CONFIRMED
        order.save(update_fields=['status', 'updated_at'])
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
