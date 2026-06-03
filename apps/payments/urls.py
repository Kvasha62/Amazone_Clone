from django.urls import path

from .views import (
    PaymentPayAPIView,
    PaymentFailAPIView,
    PaymentRefundAPIView,
)

urlpatterns = [
    path(
        '<int:payment_id>/pay/',
        PaymentPayAPIView.as_view(),
        name='payment-pay'
    ),

    path(
        '<int:payment_id>/fail/',
        PaymentFailAPIView.as_view(),
        name='payment-fail'
    ),

    path(
        '<int:payment_id>/refund/',
        PaymentRefundAPIView.as_view(),
        name='payment-refund'
    ),
]