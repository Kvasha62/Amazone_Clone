# ────────────────────────────────────────────────────────────────────────
# apps/orders/tests/test_api.py — тесты API endpoints заказов.
#
# ПОКРЫТИЕ:
#   • GET /api/v1/orders/ — список заказов (200)
#   • GET /api/v1/orders/{order_number}/ — детали (200)
#   • GET /api/v1/orders/{order_number}/ — чужой заказ (404)
#   • PATCH /api/v1/orders/{order_number}/status/ — статус (200, staff)
#   • PATCH /api/v1/orders/{order_number}/status/ — не staff (403)
#   • POST /api/v1/orders/{order_number}/cancel/ — отмена (200)
#   • Unauthenticated access (401)
#
# 📖 https://www.django-rest-framework.org/api-guide/testing/
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/tools/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Нет автопроверки API → сломанные endpoints не обнаружатся
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.orders.models.order import OrderStatus
from apps.orders.tests.factories import (
    create_test_order,
    create_test_user,
)


class OrderAPITests(TestCase):
    """Тесты API endpoints заказов."""

    def setUp(self):
        """Создаём пользователя и API-клиент."""
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.order = create_test_order(self.user)

    # ── Список заказов ──

    def test_list_orders_authenticated(self):
        """GET /api/v1/orders/ — список заказов пользователя (200)."""
        url = reverse('orders:order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_orders_unauthenticated(self):
        """GET /api/v1/orders/ без токена → 401."""
        self.client.logout()
        url = reverse('orders:order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    # ── Детали заказа ──

    def test_retrieve_own_order(self):
        """GET /api/v1/orders/{order_number}/ — свой заказ (200)."""
        url = reverse(
            'orders:order-detail',
            kwargs={'order_number': self.order.order_number},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['order_number'],
            self.order.order_number,
        )

    def test_retrieve_other_user_order_returns_404(self):
        """GET /api/v1/orders/{order_number}/ — чужой заказ → 404."""
        other_user = create_test_user()
        other_order = create_test_order(other_user)

        url = reverse(
            'orders:order-detail',
            kwargs={'order_number': other_order.order_number},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_retrieve_nonexistent_order_returns_404(self):
        """GET /api/v1/orders/ORD-999999/ — несуществующий → 404."""
        url = reverse(
            'orders:order-detail',
            kwargs={'order_number': 'ORD-999999'},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # ── Изменение статуса (staff only) ──

    def test_status_change_by_staff(self):
        """PATCH status/ staff → 200."""
        self.user.is_staff = True
        self.user.save()

        url = reverse(
            'orders:order-status',
            kwargs={'order_number': self.order.order_number},
        )
        response = self.client.patch(url, {'status': 'confirmed'})
        self.assertEqual(response.status_code, 200)

    def test_status_change_by_non_staff(self):
        """PATCH status/ не-staff → 403."""
        url = reverse(
            'orders:order-status',
            kwargs={'order_number': self.order.order_number},
        )
        response = self.client.patch(url, {'status': 'confirmed'})
        self.assertEqual(response.status_code, 403)

    # ── Отмена заказа ──

    def test_cancel_own_order(self):
        """POST cancel/ свой заказ → 200."""
        url = reverse(
            'orders:order-cancel',
            kwargs={'order_number': self.order.order_number},
        )
        response = self.client.post(url, {'reason': 'changed_mind'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'cancelled')

    def test_cancel_other_user_order_returns_404(self):
        """POST cancel/ чужой заказ → 404."""
        other_user = create_test_user()
        other_order = create_test_order(other_user)

        url = reverse(
            'orders:order-cancel',
            kwargs={'order_number': other_order.order_number},
        )
        response = self.client.post(url, {'reason': 'changed_mind'})
        self.assertEqual(response.status_code, 404)

    def test_cancel_already_cancelled_order(self):
        """POST cancel/ уже отменённый → ошибка."""
        from apps.orders.services.order_service import OrderService
        OrderService.cancel(self.order, reason='changed_mind')

        url = reverse(
            'orders:order-cancel',
            kwargs={'order_number': self.order.order_number},
        )
        response = self.client.post(url, {'reason': 'other'})
        self.assertEqual(response.status_code, 400)
