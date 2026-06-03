from django.urls import path

from .api_views import (
    CheckoutAPIView,
    OrderListAPIView
)


urlpatterns = [

    # 🛒 Checkout
    path(
        'api/orders/checkout/',
        CheckoutAPIView.as_view()
    ),

    # 📦 Orders history
    path(
        'api/orders/',
        OrderListAPIView.as_view()
    ),
]
