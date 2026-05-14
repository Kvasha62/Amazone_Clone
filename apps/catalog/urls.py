from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ProductViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')

urlpatterns = [
    path('api/', include(router.urls)),
]

