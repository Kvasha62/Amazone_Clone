from django.db import models
from apps.catalog.querysets.product_queryset import ProductQuerySet


class ProductManager(models.Manager.from_queryset(ProductQuerySet)):

    def catalog(self):
        return self.get_queryset().catalog()