# ────────────────────────────────────────────────────────────────────────
# apps/analytics/serializers/__init__.py — реэкспорт сериализаторов.
# ────────────────────────────────────────────────────────────────────────

from apps.analytics.serializers.analytics_serializers import (
    AnalyticsDateRangeSerializer,
    DashboardResponseSerializer,
    ProductViewSerializer,
    SalesSummarySerializer,
    SalesTimelineSerializer,
    TopProductSerializer,
    TopCustomerSerializer,
    TopCategorySerializer,
)

__all__ = [
    'AnalyticsDateRangeSerializer',
    'DashboardResponseSerializer',
    'ProductViewSerializer',
    'SalesSummarySerializer',
    'SalesTimelineSerializer',
    'TopProductSerializer',
    'TopCustomerSerializer',
    'TopCategorySerializer',
]
