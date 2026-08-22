# ────────────────────────────────────────────────────────────────────────
# apps/analytics/tests/test_services.py — тесты сервиса аналитики.
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.tests.factories import (
    create_test_delivered_order_with_items,
    create_test_view,
)
from apps.analytics.models import ProductView


# ================================================================
# Record View
# ================================================================

class RecordViewTests(CatalogTestCase):

    def test_record_view_guest(self):
        """Запись просмотра гостем."""
        view = AnalyticsService.record_view(
            self.product,
            session_key='test-session',
        )
        self.assertIsNotNone(view)
        self.assertEqual(view.product, self.product)

    def test_record_view_user(self):
        """Запись просмотра авторизованным."""
        user = create_test_user()
        view = AnalyticsService.record_view(self.product, user=user)
        self.assertIsNotNone(view)
        self.assertEqual(view.user, user)

    def test_record_view_increments_count(self):
        """views_count инкрементируется."""
        AnalyticsService.record_view(self.product, session_key='s1')
        self.product.refresh_from_db()
        # views_count мог быть ненулевым из setup — проверим +1
        count_after_first = self.product.views_count
        AnalyticsService.record_view(
            self.product, session_key='s2',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.views_count, count_after_first + 1)

    def test_deduplication_same_session(self):
        """Дедупликация: та же сессия в течение часа → None."""
        AnalyticsService.record_view(self.product, session_key='dup')
        result = AnalyticsService.record_view(
            self.product, session_key='dup',
        )
        self.assertIsNone(result)

    def test_deduplication_same_user(self):
        """Дедупликация: тот же пользователь в течение часа → None."""
        user = create_test_user()
        AnalyticsService.record_view(self.product, user=user)
        result = AnalyticsService.record_view(
            self.product, user=user,
        )
        self.assertIsNone(result)

    def test_no_dedup_different_session(self):
        """Разные сессии → оба просмотра записаны."""
        v1 = AnalyticsService.record_view(
            self.product, session_key='sess-a',
        )
        v2 = AnalyticsService.record_view(
            self.product, session_key='sess-b',
        )
        self.assertIsNotNone(v1)
        self.assertIsNotNone(v2)


# ================================================================
# Sales Summary
# ================================================================

class SalesSummaryTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=2,
            unit_price=Decimal('1000.00'),
        )

    def test_summary_has_revenue(self):
        """Сводка содержит выручку."""
        summary = AnalyticsService.get_sales_summary(days=30)
        self.assertGreater(summary['total_revenue'], 0)

    def test_summary_total_orders(self):
        """Сводка считает заказы."""
        summary = AnalyticsService.get_sales_summary(days=30)
        self.assertEqual(summary['total_orders'], 1)

    def test_summary_delivered_orders(self):
        """Доставленные заказы посчитаны."""
        summary = AnalyticsService.get_sales_summary(days=30)
        self.assertEqual(summary['delivered_orders'], 1)

    def test_summary_avg_order_value(self):
        """Средний чек посчитан."""
        summary = AnalyticsService.get_sales_summary(days=30)
        self.assertGreater(summary['avg_order_value'], 0)

    def test_summary_items_sold(self):
        """Проданные единицы посчитаны."""
        summary = AnalyticsService.get_sales_summary(days=30)
        self.assertEqual(summary['total_items_sold'], 2)

    def test_summary_empty_period(self):
        """Пустой период — нули."""
        summary = AnalyticsService.get_sales_summary(days=0)
        # days=0 → start_date=now → может поймать текущий заказ
        # используем явные даты в будущем
        future = timezone.now() + timezone.timedelta(days=10)
        summary = AnalyticsService.get_sales_summary(
            start_date=future,
            end_date=future + timezone.timedelta(days=1),
        )
        self.assertEqual(summary['total_revenue'], Decimal('0'))
        self.assertEqual(summary['total_orders'], 0)


# ================================================================
# Sales Timeline
# ================================================================

class SalesTimelineTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=1,
            unit_price=Decimal('500.00'),
            days_ago=5,
        )

    def test_timeline_has_data(self):
        """Временной ряд содержит данные."""
        timeline = AnalyticsService.get_sales_timeline(days=30)
        self.assertGreater(len(timeline), 0)

    def test_timeline_structure(self):
        """Структура элементов временного ряда."""
        timeline = AnalyticsService.get_sales_timeline(days=7)
        for item in timeline:
            self.assertIn('date', item)
            self.assertIn('orders_count', item)
            self.assertIn('revenue', item)
            self.assertIn('items_sold', item)

    def test_timeline_period_daily(self):
        """Шаг daily — по одному элементу на день."""
        timeline = AnalyticsService.get_sales_timeline(days=7, period='daily')
        self.assertGreater(len(timeline), 0)


# ================================================================
# Top Products
# ================================================================

class TopProductsTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        # Товар 1: 5 шт по 1000 = 5000
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=5, unit_price=Decimal('1000.00'),
        )
        # Товар 2: 2 шт по 2000 = 4000
        create_test_delivered_order_with_items(
            self.user, self.variant_256,
            quantity=2, unit_price=Decimal('2000.00'),
        )

    def test_top_products_by_revenue(self):
        """Топ по выручке."""
        top = AnalyticsService.get_top_products(days=30, metric='revenue')
        self.assertEqual(len(top), 2)
        # variant_128: 5*1000=5000 > variant_256: 2*2000=4000
        self.assertEqual(top[0]['variant_id'], self.variant_128.pk)
        self.assertEqual(top[0]['quantity_sold'], 5)

    def test_top_products_by_quantity(self):
        """Топ по количеству."""
        top = AnalyticsService.get_top_products(days=30, metric='quantity')
        # variant_128: 5 шт > variant_256: 2 шт
        self.assertEqual(top[0]['variant_id'], self.variant_128.pk)

    def test_top_products_limit(self):
        """Лимит количества."""
        top = AnalyticsService.get_top_products(days=30, limit=1)
        self.assertEqual(len(top), 1)

    def test_top_products_empty(self):
        """Пустой результат при отсутствии заказов."""
        top = AnalyticsService.get_top_products(days=0)
        self.assertEqual(len(top), 0)


# ================================================================
# Top Categories
# ================================================================

class TopCategoriesTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=3, unit_price=Decimal('1500.00'),
        )

    def test_top_categories(self):
        """Топ категорий."""
        top = AnalyticsService.get_top_categories(days=30)
        self.assertGreater(len(top), 0)
        self.assertIn('category_name', top[0])
        self.assertIn('revenue', top[0])

    def test_top_categories_limit(self):
        """Лимит."""
        top = AnalyticsService.get_top_categories(days=30, limit=5)
        self.assertLessEqual(len(top), 5)


# ================================================================
# Top Customers
# ================================================================

class TopCustomersTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=1, unit_price=Decimal('2000.00'),
        )

    def test_top_customers(self):
        """Топ покупателей."""
        top = AnalyticsService.get_top_customers(days=30)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]['user_id'], self.user.pk)
        self.assertIn('email', top[0])

    def test_top_customers_limit(self):
        """Лимит."""
        top = AnalyticsService.get_top_customers(days=30, limit=5)
        self.assertLessEqual(len(top), 5)


# ================================================================
# Conversion Rate
# ================================================================

class ConversionRateTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        # 10 просмотров
        for i in range(10):
            create_test_view(self.product, session_key=f'sess-{i}')

    def test_conversion_no_orders(self):
        """Конверсия без заказов = 0%."""
        result = AnalyticsService.get_conversion_rate(days=30)
        self.assertEqual(result['total_views'], 10)
        self.assertEqual(result['total_orders'], 0)
        self.assertEqual(result['conversion_rate'], Decimal('0'))

    def test_conversion_with_orders(self):
        """Конверсия с заказами > 0%."""
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=1, unit_price=Decimal('100.00'),
        )
        result = AnalyticsService.get_conversion_rate(days=30)
        self.assertGreater(result['total_orders'], 0)
        self.assertGreater(result['conversion_rate'], Decimal('0'))


# ================================================================
# Product Views Stats
# ================================================================

class ProductViewsTests(CatalogTestCase):

    def setUp(self):
        for i in range(5):
            create_test_view(
                self.product,
                session_key=f'sess-{i}',
                source='organic',
            )

    def test_product_views_stats(self):
        """Статистика просмотров товара."""
        stats = AnalyticsService.get_product_views(self.product, days=30)
        self.assertEqual(stats['total_views'], 5)

    def test_product_views_by_source(self):
        """Просмотры по источникам."""
        create_test_view(self.product, session_key='s-direct', source='direct')
        stats = AnalyticsService.get_product_views(self.product, days=30)
        self.assertIn('organic', stats['by_source'])

    def test_most_viewed_products(self):
        """Самые просматриваемые товары."""
        result = AnalyticsService.get_most_viewed_products(days=30)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]['product_id'], self.product.pk)
        self.assertEqual(result[0]['views_count'], 5)


# ================================================================
# Dashboard
# ================================================================

class DashboardTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        create_test_delivered_order_with_items(
            self.user, self.variant_128,
            quantity=1, unit_price=Decimal('1000.00'),
        )
        create_test_view(self.product, session_key='sess-dash')

    def test_dashboard_structure(self):
        """Дашборд содержит все секции."""
        data = AnalyticsService.get_dashboard(days=30)
        self.assertIn('summary', data)
        self.assertIn('top_products', data)
        self.assertIn('top_categories', data)
        self.assertIn('top_customers', data)
        self.assertIn('conversion', data)
        self.assertIn('timeline', data)

    def test_dashboard_summary_has_revenue(self):
        """В дашборде есть выручка."""
        data = AnalyticsService.get_dashboard(days=30)
        self.assertGreater(data['summary']['total_revenue'], 0)
