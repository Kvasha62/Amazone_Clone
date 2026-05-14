from django.urls import path

from .api_views import CartAPIView


urlpatterns = [
    path('api/cart/', CartAPIView.as_view()),
]