# ────────────────────────────────────────────────────────────────────────
# apps/payments/urls.py — URL-маршруты для API платежей.
#
# ПОДКЛЮЧЕНИЕ В config/urls.py:
#   path('api/v1/payments/', include('apps.payments.urls'))
#
# ПОЛНЫЙ СПИСОК ЭНДПОИНТОВ:
#   GET    /api/v1/payments/                              — список платежей
#   POST   /api/v1/payments/                              — создать платёж
#   POST   /api/v1/payments/webhook/                      — вебхук (внешний)
#   GET    /api/v1/payments/{payment_number}/             — детали платежа
#   POST   /api/v1/payments/{payment_number}/refund/      — возврат (staff)
#   POST   /api/v1/payments/{payment_number}/cancel/      — отмена
#
# ПОЧЕМУ payment_number В URL, А НЕ id:
#   Аналогично orders: id — внутренний, payment_number — публичный.
#   PAY-000001 удобнее для отладки и не раскрывает PK.
#
# ВАЖНО: порядок маршрутов имеет значение!
#   Статический путь ('webhook/') ДО динамического (<str:payment_number>/).
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.payments.api_views import (
    PaymentCancelView,
    PaymentDetailView,
    PaymentListView,
    PaymentRefundView,
    PaymentWebhookView,
)

app_name = 'payments'

urlpatterns = [
    # GET/POST /api/v1/payments/
    path('', PaymentListView.as_view(), name='payment-list'),

    # POST /api/v1/payments/webhook/
    # Статический путь — ДО динамического (payment_number).
    path('webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),

    # GET /api/v1/payments/{payment_number}/
    path('<str:payment_number>/', PaymentDetailView.as_view(), name='payment-detail'),

    # POST /api/v1/payments/{payment_number}/refund/
    path(
        '<str:payment_number>/refund/',
        PaymentRefundView.as_view(),
        name='payment-refund',
    ),

    # POST /api/v1/payments/{payment_number}/cancel/
    path(
        '<str:payment_number>/cancel/',
        PaymentCancelView.as_view(),
        name='payment-cancel',
    ),
]
