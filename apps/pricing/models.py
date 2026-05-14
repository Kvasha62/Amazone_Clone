from django.db import models
from apps.catalog.models import ProductVariant


class Price(models.Model):
    variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='price'
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    currency = models.CharField(max_length=10, default='USD')

    def __str__(self):
        return f"{self.variant.sku} - {self.price}"