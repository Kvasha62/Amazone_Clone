from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(ReadOnlyModelViewSet):

    serializer_class = ProductSerializer

    filter_backends = [DjangoFilterBackend]

    filterset_fields = [
        'category__slug',
        'brand'
    ]

    # 🔥 ОПТИМИЗАЦИЯ SQL
    queryset = Product.objects.prefetch_related(
        'variants',
        'variants__price',
        'variants__stock',
        'images'
    )