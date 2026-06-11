from django.urls import path

from apps.cart.api_views import (
    CartView,
    CartItemView,
    CartItemDetailView,
    CartMergeView,
)

app_name = 'cart'

# Префикс /api/v1/cart/ подключается в проектном config/urls.py:
#   path('api/v1/cart/', include('apps.cart.urls')),
urlpatterns = [
    path('', CartView.as_view(), name='cart'),
    path('items/', CartItemView.as_view(), name='cart-items'),
    path('items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('merge/', CartMergeView.as_view(), name='cart-merge'),
]
