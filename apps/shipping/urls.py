# ────────────────────────────────────────────────────────────────────────
# apps/shipping/urls.py — URL-маршруты для API доставки.
#
# ПОДКЛЮЧЕНИЕ В config/urls.py:
#   path('api/v1/shipping/', include('apps.shipping.urls'))
#
# ПОЛНЫЙ СПИСОК ЭНДПОИНТОВ:
#   GET    /api/v1/shipping/methods/                     — способы доставки
#   POST   /api/v1/shipping/calculate/                   — расчёт стоимости
#   GET    /api/v1/shipping/shipments/                   — список отправлений
#   POST   /api/v1/shipping/shipments/                   — создать (staff)
#   GET    /api/v1/shipping/shipments/{id}/              — детали
#   PATCH  /api/v1/shipping/shipments/{id}/status/       — статус (staff)
#   POST   /api/v1/shipping/shipments/{id}/tracking/     — трек-номер (staff)
#   GET    /api/v1/shipping/track/{tracking}/            — отслеживание (public)
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.shipping.api_views import (
    ShipmentCreateView,
    ShipmentDetailView,
    ShipmentListView,
    ShipmentStatusView,
    ShipmentTrackingByCodeView,
    ShipmentTrackingView,
    ShippingCostView,
    ShippingMethodListView,
)

app_name = 'shipping'

urlpatterns = [
    # ── Способы доставки ──
    path('methods/', ShippingMethodListView.as_view(), name='method-list'),
    path('calculate/', ShippingCostView.as_view(), name='calculate'),

    # ── Отправления ──
    path('shipments/', ShipmentListView.as_view(), name='shipment-list'),
    path('shipments/create/', ShipmentCreateView.as_view(), name='shipment-create'),
    path('shipments/<int:pk>/', ShipmentDetailView.as_view(), name='shipment-detail'),
    path(
        'shipments/<int:pk>/status/',
        ShipmentStatusView.as_view(),
        name='shipment-status',
    ),
    path(
        'shipments/<int:pk>/tracking/',
        ShipmentTrackingView.as_view(),
        name='shipment-tracking',
    ),

    # ── Публичное отслеживание ──
    path(
        'track/<str:tracking>/',
        ShipmentTrackingByCodeView.as_view(),
        name='track-by-code',
    ),
]
