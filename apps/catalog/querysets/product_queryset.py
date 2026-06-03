from django.db import models
from django.db.models import Prefetch


class ProductQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            is_active=True
        )

    def active_categories(self):
        return self.filter(
            category__is_active=True
        )

    def with_related(self):
        return self.select_related(
            'brand',
            'category'
        )

    def with_images(self):
        return self.prefetch_related(
            'images'
        )

    def with_variants(self):

        from apps.catalog.models.product_variant import ProductVariant

        variants_queryset = (
            ProductVariant.objects
            .filter(is_active=True)
            .select_related(
                'price',
                'stock'
            )
        )

        return self.prefetch_related(
            Prefetch(
                'variants',
                queryset=variants_queryset
            )
        )

    def catalog(self):
        return (
            self.visible()
            .with_related()
            .with_images()
            .with_variants()
        )

    def visible(self):
        return (
            self.active()
            .active_categories()
        )