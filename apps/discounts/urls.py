from django.urls import path
from apps.discounts.api_views import (
    CouponApplyView,
    CouponListView,
    CouponPreviewView,
    CouponRemoveView,
)

app_name = 'discounts'

urlpatterns = [
    path('coupons/', CouponListView.as_view(), name='coupon-list'),
    path('apply/', CouponApplyView.as_view(), name='coupon-apply'),
    path('remove/', CouponRemoveView.as_view(), name='coupon-remove'),
    path('preview/', CouponPreviewView.as_view(), name='coupon-preview'),
]
