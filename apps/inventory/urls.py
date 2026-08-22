# ────────────────────────────────────────────────────────────────────────
# apps/inventory/urls.py — URL-маршруты для API склада.
#
# ПОДКЛЮЧЕНИЕ В config/urls.py:
#   path('api/v1/inventory/', include('apps.inventory.urls'))
#
# ЭНДПОИНТЫ:
#   GET  /api/v1/inventory/                            — список остатков
#   GET  /api/v1/inventory/{variant_id}/               — остатки варианта
#   POST /api/v1/inventory/{variant_id}/restock/       — пополнение
#   POST /api/v1/inventory/{variant_id}/adjust/        — корректировка
#   GET  /api/v1/inventory/{variant_id}/movements/     — история
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Все 5 endpoints склада → 404
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.inventory.api_views import (
    StockAdjustView,
    StockDetailView,
    StockListView,
    StockMovementListView,
    StockRestockView,
)

app_name = 'inventory'

urlpatterns = [
    # GET /api/v1/inventory/
    path('', StockListView.as_view(), name='stock-list'),

    # GET /api/v1/inventory/{variant_id}/
    path('<int:variant_id>/', StockDetailView.as_view(), name='stock-detail'),

    # POST /api/v1/inventory/{variant_id}/restock/
    path(
        '<int:variant_id>/restock/',
        StockRestockView.as_view(),
        name='stock-restock',
    ),

    # POST /api/v1/inventory/{variant_id}/adjust/
    path(
        '<int:variant_id>/adjust/',
        StockAdjustView.as_view(),
        name='stock-adjust',
    ),

    # GET /api/v1/inventory/{variant_id}/movements/
    path(
        '<int:variant_id>/movements/',
        StockMovementListView.as_view(),
        name='stock-movements',
    ),
]
