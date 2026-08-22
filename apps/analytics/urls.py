# ────────────────────────────────────────────────────────────────────────
# apps/analytics/urls.py — URL-маршруты для API аналитики.
#
# ПОДКЛЮЧЕНИЕ В config/urls.py:
#   path('api/v1/analytics/', include('apps.analytics.urls'))
#
# Все endpoints требуют IsAdminUser.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.analytics.api_views import (
    ConversionView,
    DashboardView,
    MostViewedProductsView,
    SalesSummaryView,
    SalesTimelineView,
    TopCategoriesView,
    TopCustomersView,
    TopProductsView,
)

app_name = 'analytics'

urlpatterns = [
    # ── Комплексный дашборд ──
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # ── Продажи ──
    path('sales/', SalesSummaryView.as_view(), name='sales-summary'),
    path('sales/timeline/', SalesTimelineView.as_view(), name='sales-timeline'),

    # ── Топы ──
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('top-categories/', TopCategoriesView.as_view(), name='top-categories'),
    path('top-customers/', TopCustomersView.as_view(), name='top-customers'),

    # ── Конверсия и просмотры ──
    path('conversion/', ConversionView.as_view(), name='conversion'),
    path('most-viewed/', MostViewedProductsView.as_view(), name='most-viewed'),
]
