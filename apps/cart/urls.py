# ────────────────────────────────────────────────────────────────────────
# apps/cart/urls.py — URL-маршруты для API корзины.
#
# ПОДКЛЮЧЕНИЕ В config/urls.py:
#   path('api/v1/cart/', include('apps.cart.urls'))
#
# ПОЛНЫЙ СПИСОК ЭНДПОИНТОВ:
#   GET    /api/v1/cart/                  — получить корзину
#   DELETE /api/v1/cart/                  — очистить корзину
#   POST   /api/v1/cart/items/            — добавить товар
#   PATCH  /api/v1/cart/items/{id}/       — изменить количество
#   DELETE /api/v1/cart/items/{id}/       — удалить позицию
#   POST   /api/v1/cart/merge/            — слить гостевую корзину
#
# ПОЧЕМУ НЕ РЕСУРС-ОРИЕНТИРОВАННЫЕ URL:
#   /cart/items/ — множественное число (REST convention)
#   /cart/merge/ — глагол (исключение для не-CRUD операции)
#   Альтернатива: POST /cart/ с action=merge — менее RESTful.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
# 📖 https://www.django-rest-framework.org/tutorial/2-requests-and-responses/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   Все 5 endpoints корзины → 404
# ────────────────────────────────────────────────────────────────────────

# path — функция Django для определения URL-маршрутов.
from django.urls import path

# Импортируем все view-классы.
from apps.cart.api_views import (
    CartView,
    CartItemView,
    CartItemDetailView,
    CartMergeView,
)

# app_name — namespace для reverse():
#   reverse('cart:cart') → '/api/v1/cart/'
#   reverse('cart:cart-items') → '/api/v1/cart/items/'
# Без namespace: risk конфликта с другими приложениями.
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/#url-namespaces
app_name = 'cart'

# Полный URL = 'api/v1/cart/' (из config/urls.py) + путь из urlpatterns.

urlpatterns = [
    # GET/DELETE /api/v1/cart/
    # Имя 'cart' — для reverse('cart:cart')
    path('', CartView.as_view(), name='cart'),

    # POST /api/v1/cart/items/
    # Имя 'cart-items' — для reverse('cart:cart-items')
    path('items/', CartItemView.as_view(), name='cart-items'),

    # PATCH/DELETE /api/v1/cart/items/{id}/
    # <int:item_id> — конвертер: только целые числа.
    # Django вернёт 404 если item_id не int.
    path('items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),

    # POST /api/v1/cart/merge/
    # Должен быть ПОСЛЕ items/ — иначе 'merge' воспримется как item_id.
    # Но <int:item_id> не совпадёт со строкой 'merge' → порядок не критичен.
    # Тем не менее, хороший тон — размещать статические маршруты до динамических.
    path('merge/', CartMergeView.as_view(), name='cart-merge'),
]
