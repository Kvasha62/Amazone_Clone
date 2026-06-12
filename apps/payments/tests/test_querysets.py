# ────────────────────────────────────────────────────────────────────────
# apps/payments/tests/test_querysets.py — тесты PaymentQuerySet.
#
# ПРОВЕРЯЕТ:
#   • Фильтрация по статусу (pending, succeeded, failed, etc.)
#   • Фильтрация по связям (for_order, for_user, for_provider)
#   • Оптимизация (with_order, with_user, with_events)
#   • Агрегация (total_paid)
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from apps.orders.tests.factories import create_test_order, create_test_user
from apps.payments.tests.factories import create_test_payment


class PaymentQuerySetTests(TestCase):
    """Тесты PaymentQuerySet chainable-методов."""

    def setUp(self):
        self.user = create_test_user()
        self.user2 = create_test_user()
        self.order = create_test_order(self.user)
        self.order2 = create_test_order(self.user2)

        self.payment_pending = create_test_payment(
            self.order, self.user, status='pending',
        )
        self.payment_succeeded = create_test_payment(
            self.order, self.user, status='succeeded',
        )
        self.payment_failed = create_test_payment(
            self.order2, self.user2, status='failed',
        )
        self.payment_cancelled = create_test_payment(
            self.order, self.user, status='cancelled',
        )
        self.payment_refunded = create_test_payment(
            self.order, self.user,
            status='refunded',
            refund_amount=Decimal('500.00'),
        )

    # ── Фильтрация по статусу ──

    def test_pending(self):
        qs = Payment.objects.pending()
        self.assertIn(self.payment_pending, qs)
        self.assertNotIn(self.payment_succeeded, qs)

    def test_succeeded(self):
        qs = Payment.objects.succeeded()
        self.assertIn(self.payment_succeeded, qs)
        self.assertNotIn(self.payment_pending, qs)

    def test_failed(self):
        qs = Payment.objects.failed()
        self.assertIn(self.payment_failed, qs)
        self.assertNotIn(self.payment_pending, qs)

    def test_cancelled(self):
        qs = Payment.objects.cancelled()
        self.assertIn(self.payment_cancelled, qs)
        self.assertNotIn(self.payment_pending, qs)

    def test_refunded(self):
        qs = Payment.objects.refunded()
        self.assertIn(self.payment_refunded, qs)
        self.assertNotIn(self.payment_pending, qs)

    def test_terminal(self):
        qs = Payment.objects.terminal()
        self.assertIn(self.payment_failed, qs)
        self.assertIn(self.payment_cancelled, qs)
        self.assertIn(self.payment_refunded, qs)
        self.assertNotIn(self.payment_pending, qs)
        self.assertNotIn(self.payment_succeeded, qs)

    def test_active(self):
        """active = не терминальные (PENDING, PROCESSING, SUCCEEDED)."""
        qs = Payment.objects.active()
        self.assertIn(self.payment_pending, qs)
        self.assertIn(self.payment_succeeded, qs)
        self.assertNotIn(self.payment_failed, qs)
        self.assertNotIn(self.payment_cancelled, qs)

    # ── Фильтрация по связям ──

    def test_for_order(self):
        qs = Payment.objects.for_order(self.order)
        for p in qs:
            self.assertEqual(p.order_id, self.order.pk)

    def test_for_user(self):
        qs = Payment.objects.for_user(self.user)
        for p in qs:
            self.assertEqual(p.user_id, self.user.pk)

    def test_for_provider(self):
        qs = Payment.objects.for_provider('mock')
        self.assertEqual(qs.count(), 5)

    # ── Оптимизация ──

    def test_with_order(self):
        payment = Payment.objects.with_order().first()
        # select_related('order') → обращение к order без доп. SQL
        self.assertIsNotNone(payment.order)

    def test_with_user(self):
        payment = Payment.objects.with_user().first()
        self.assertIsNotNone(payment.user)

    def test_with_events(self):
        payment = Payment.objects.with_events().first()
        # prefetch_related — не падает
        list(payment.events.all())

    # ── Агрегация ──

    def test_total_paid(self):
        total = Payment.objects.for_user(self.user).total_paid()
        self.assertEqual(total, self.payment_succeeded.amount)


# Импорт Payment для тестов
from apps.payments.models import Payment
