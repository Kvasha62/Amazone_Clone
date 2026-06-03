# from django.db import models
# from apps.catalog.models import ProductVariant
#
#
# class Price(models.Model):
#     variant = models.OneToOneField(
#         ProductVariant,
#         on_delete=models.CASCADE,
#         related_name='price'
#     )
#
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#
#     currency = models.CharField(max_length=10, default='USD')
#
#     def __str__(self):
#         return f"{self.variant.sku} - {self.price}"

from django.db import models

from apps.catalog.models import ProductVariant
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class Price(models.Model):

    variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='price',
        verbose_name='Вариант товара'
    )

    price = models.DecimalField(
        'Текущая цена',
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    old_price = models.DecimalField(
        'Старая цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0)
        ]
    )

    currency = models.CharField(
        'Валюта',
        max_length=10,
        default='USD'
    )

    class Meta:
        verbose_name = 'Цена'
        verbose_name_plural = 'Цены'

        indexes = [
            models.Index(fields=['currency']),
        ]

    def __str__(self):
        return f'{self.variant.sku} - {self.price}'

    @property
    def discount_percent(self):

        if (
                not self.old_price
                or self.old_price <= self.price
        ):
            return 0

        return round(
            (
                    (self.old_price - self.price)
                    / self.old_price
            ) * 100
        )

    def clean(self):

        if (
                self.old_price
                and self.old_price < self.price
        ):
            raise ValidationError(
                'Старая цена не может быть меньше текущей.'
            )