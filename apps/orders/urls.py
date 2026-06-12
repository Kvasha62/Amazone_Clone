# ────────────────────────────────────────────────────────────────────────
# apps/orders/urls.py — URL-маршруты для API заказов.
#
# ПОДКЛЮЧЕНИЕ В config/urls.py:
#   path('api/v1/orders/', include('apps.orders.urls'))
#
# ПОЛНЫЙ СПИСОК ЭНДПОИНТОВ:
#   GET    /api/v1/orders/                              — список заказов
#   POST   /api/v1/orders/                              — оформить заказ
#   GET    /api/v1/orders/{order_number}/               — детали заказа
#   PATCH  /api/v1/orders/{order_number}/status/        — статус (staff)
#   POST   /api/v1/orders/{order_number}/cancel/        — отмена
#
# ПОЧЕМУ order_number В URL, А НЕ id:
#   • id — внутренний PK (может раскрывать бизнес-данные)
#   • order_number — публичный идентификатор (ORD-000001)
#   • UX: пользователь копирует ссылку с order_number
#   • Безопасность: невозможно угадать следующий/предыдущий id
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
# 📖 https://www.django-rest-framework.org/tutorial/2-requests-and-responses/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Все 5 endpoints заказов → 404
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.orders.api_views import (
    OrderCancelView,
    OrderDetailView,
    OrderListView,
    OrderStatusView,
)

# app_name — namespace для reverse():
#   reverse('orders:order-list') → '/api/v1/orders/'
#   reverse('orders:order-detail', kwargs={'order_number': 'ORD-000001'})
# Без namespace: risk конфликта с другими приложениями.
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/#url-namespaces
app_name = 'orders'

# Полный URL = 'api/v1/orders/' (из config/urls.py) + путь из urlpatterns.
#
# ВАЖНО: порядок маршрутов имеет значение!
# Статические пути ('status/', 'cancel/') должны быть ДО
# динамического (<str:order_number>/).
# Иначе Django воспримет 'status' как order_number → OrderDetailView.

urlpatterns = [
    # GET/POST /api/v1/orders/
    path('', OrderListView.as_view(), name='order-list'),

    # GET /api/v1/orders/{order_number}/
    # <str:order_number> — строковый конвертер (ORD-000001).
    path('<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),

    # PATCH /api/v1/orders/{order_number}/status/
    # Статический путь — ДО detail (хотя <str:> не совпадёт с 'status').
    path(
        '<str:order_number>/status/',
        OrderStatusView.as_view(),
        name='order-status',
    ),

    # POST /api/v1/orders/{order_number}/cancel/
    path(
        '<str:order_number>/cancel/',
        OrderCancelView.as_view(),
        name='order-cancel',
    ),
]
