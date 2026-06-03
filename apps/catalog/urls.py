from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.catalog.api.product_views import ProductViewSet

router = DefaultRouter()

router.register(
    r'products',
    ProductViewSet,
    basename='products'
)

urlpatterns = [
    path('api/', include(router.urls)),
]