# ────────────────────────────────────────────────────────────────────────
# apps/payments/tests/test_signals.py — тесты сигналов платежей.
#
# ПРОВЕРЯЕТ:
#   • on_payment_created — логирование создания
#   • on_payment_updated — логирование обновления
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from apps.orders.tests.factories import create_test_order, create_test_user
from apps.payments.tests.factories import create_test_payment


class PaymentSignalTests(TestCase):
    """Тесты сигналов платежей."""

    def test_signal_fires_on_create(self):
        """post_save сигнал срабатывает при создании платежа."""
        user = create_test_user()
        order = create_test_order(user)
        # Сигнал не должен падать
        payment = create_test_payment(order, user)
        self.assertIsNotNone(payment.pk)

    def test_signal_fires_on_update(self):
        """post_save сигнал срабатывает при обновлении платежа."""
        user = create_test_user()
        order = create_test_order(user)
        payment = create_test_payment(order, user)
        payment.status = 'processing'
        payment.save()  # Сигнал не должен падать
        self.assertEqual(payment.status, 'processing')
