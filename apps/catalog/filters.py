import django_filters

from django_filters import (
    FilterSet,
    NumberFilter,
    CharFilter,
    BooleanFilter,
)

from apps.catalog.models import Product
from django.db.models import Q


class ProductFilter(FilterSet):
    """
    Фильтрация товаров каталога.
    """

    brand = CharFilter(
        field_name='brand__slug',
        lookup_expr='exact'
    )

    category = CharFilter(
        field_name='category__slug',
        lookup_expr='exact'
    )

    min_price = NumberFilter(
        field_name='variants__price__price',
        lookup_expr='gte'
    )

    max_price = NumberFilter(
        field_name='variants__price__price',
        lookup_expr='lte'
    )

    min_rating = NumberFilter(
        field_name='rating',
        lookup_expr='gte'
    )

    is_active = BooleanFilter(
        field_name='is_active'
    )

    search = CharFilter(
        method='filter_search'
    )

    def filter_search(
            self,
            queryset,
            name,
            value
    ):
        return queryset.filter(
            Q(name__icontains=value)
            |
            Q(description__icontains=value)
            |
            Q(brand__name__icontains=value)
        )

    @property
    def qs(self):
        parent = super().qs

        return parent.distinct()

    class Meta:
        model = Product

        fields = (
            'brand',
            'category',
            'is_active',
            'min_price',
            'max_price',
            'min_rating',
            'search',
        )
