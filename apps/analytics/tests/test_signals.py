# ────────────────────────────────────────────────────────────────────────
# apps/analytics/tests/test_signals.py — тесты сигналов аналитики.
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase
from apps.catalog.tests.factories import CatalogTestCase
from apps.analytics.services.analytics_service import AnalyticsService


class AnalyticsSignalTests(CatalogTestCase):

    def test_signal_on_view_recorded(self):
        """Сигнал product_view_signal срабатывает при создании просмотра."""
        with self.assertLogs('apps.analytics.signals', level='INFO') as cm:
            AnalyticsService.record_view(
                self.product,
                session_key='signal-test',
            )
        self.assertTrue(
            any('product_view_signal' in m for m in cm.output)
        )
