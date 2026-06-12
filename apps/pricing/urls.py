# ────────────────────────────────────────────────────────────────────────
# apps/pricing/urls.py — URL-маршруты модуля ценообразования.
#
# Подключается в config/urls.py:
#   path('api/v1/', include('apps.pricing.urls'))
#
# Все endpoints — только для staff (IsAdminUser).
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.pricing.api_views import (
    PriceDetailView,
    PriceHistoryView,
    BulkPriceView,
)

app_name = 'pricing'

urlpatterns = [
    # GET/POST /api/v1/pricing/variants/<variant_id>/price/
    # <int:variant_id> — только целые числа (PK варианта).
    path(
        'pricing/variants/<int:variant_id>/price/',
        PriceDetailView.as_view(),
        name='variant-price',
    ),
    # GET /api/v1/pricing/variants/<variant_id>/history/
    path(
        'pricing/variants/<int:variant_id>/history/',
        PriceHistoryView.as_view(),
        name='variant-price-history',
    ),
    # POST /api/v1/pricing/prices/bulk/
    # Массовое обновление цен (несколько вариантов за один запрос).
    path(
        'pricing/prices/bulk/',
        BulkPriceView.as_view(),
        name='bulk-price',
    ),
]
