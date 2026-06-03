# from django.db import models
# from apps.catalog.models import ProductVariant
#
#
# class Stock(models.Model):
#     variant = models.OneToOneField(
#         ProductVariant,
#         on_delete=models.CASCADE,
#         related_name='stock'
#     )
#
#     quantity = models.PositiveIntegerField(default=0)
#
#     def __str__(self):
#         return f"{self.variant.sku} - {self.quantity}"

from django.db import models

from apps.catalog.models import ProductVariant


class Stock(models.Model):

    variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='stock',
        verbose_name='Вариант товара'
    )

    quantity = models.PositiveIntegerField(
        'Количество на складе',
        default=0
    )

    class Meta:
        verbose_name = 'Остаток на складе'
        verbose_name_plural = 'Остатки на складе'

    def __str__(self):
        return f'{self.variant.sku} - {self.quantity}'