from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend

from apps.catalog.models import Product
from apps.catalog.filters import ProductFilter
from apps.catalog.serializers import ProductSerializer
from apps.catalog.pagination.catalog_pagination import (
    CatalogPagination
)


class ProductViewSet(ReadOnlyModelViewSet):
    """
    API каталога товаров.

    Примеры:

    /api/products/

    /api/products/?brand=apple

    /api/products/?category=smartphones

    /api/products/?search=iphone

    /api/products/?min_price=500

    /api/products/?max_price=2000

    /api/products/?min_rating=4

    /api/products/?ordering=name

    /api/products/?ordering=-created_at

    /api/products/?ordering=-rating
    """

    serializer_class = ProductSerializer

    pagination_class = CatalogPagination

    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
    ]

    filterset_class = ProductFilter

    ordering_fields = (
        'name',
        'rating',
        'created_at',
        'updated_at',
    )

    ordering = (
        'name',
    )

    def get_queryset(self):
        return (
            Product.objects
            .catalog()
        )