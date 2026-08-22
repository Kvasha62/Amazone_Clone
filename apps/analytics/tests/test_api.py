# ────────────────────────────────────────────────────────────────────────
# apps/analytics/tests/test_api.py — тесты API endpoints аналитики.
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.analytics.tests.factories import (
    create_test_delivered_order_with_items,
    create_test_view,
)


class AnalyticsAPITestBase(CatalogTestCase):
    """Базовый класс с общим setUp для API тестов."""

    def setUp(self):
        self.admin = create_test_user(is_staff=True)
        self.regular_user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        # Тестовые данные
        create_test_delivered_order_with_items(
            self.admin, self.variant_128,
            quantity=2, unit_price=Decimal('1000.00'),
        )
        create_test_view(self.product, session_key='api-sess')


class DashboardAPITests(AnalyticsAPITestBase):

    def test_dashboard(self):
        """GET dashboard — все секции."""
        url = reverse('analytics:dashboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('summary', resp.data)
        self.assertIn('top_products', resp.data)

    def test_dashboard_requires_staff(self):
        """Дашборд требует staff."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('analytics:dashboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_requires_auth(self):
        """Дашборд требует авторизацию."""
        self.client.logout()
        url = reverse('analytics:dashboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class SalesSummaryAPITests(AnalyticsAPITestBase):

    def test_sales_summary(self):
        """GET sales summary."""
        url = reverse('analytics:sales-summary')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_revenue', resp.data)
        self.assertIn('total_orders', resp.data)

    def test_sales_summary_custom_days(self):
        """GET sales summary с days=7."""
        url = reverse('analytics:sales-summary')
        resp = self.client.get(url, {'days': 7})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class SalesTimelineAPITests(AnalyticsAPITestBase):

    def test_timeline(self):
        """GET timeline."""
        url = reverse('analytics:sales-timeline')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('timeline', resp.data)
        self.assertIsInstance(resp.data['timeline'], list)


class TopProductsAPITests(AnalyticsAPITestBase):

    def test_top_products(self):
        """GET top-products."""
        url = reverse('analytics:top-products')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_top_products_by_quantity(self):
        """GET top-products?metric=quantity."""
        url = reverse('analytics:top-products')
        resp = self.client.get(url, {'metric': 'quantity'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class TopCategoriesAPITests(AnalyticsAPITestBase):

    def test_top_categories(self):
        """GET top-categories."""
        url = reverse('analytics:top-categories')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)


class TopCustomersAPITests(AnalyticsAPITestBase):

    def test_top_customers(self):
        """GET top-customers."""
        url = reverse('analytics:top-customers')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)


class ConversionAPITests(AnalyticsAPITestBase):

    def test_conversion(self):
        """GET conversion."""
        url = reverse('analytics:conversion')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('conversion_rate', resp.data)
        self.assertIn('total_views', resp.data)


class MostViewedAPITests(AnalyticsAPITestBase):

    def test_most_viewed(self):
        """GET most-viewed."""
        url = reverse('analytics:most-viewed')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
