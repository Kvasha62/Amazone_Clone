from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel


class ProductImage(BaseModel):

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )

    image = models.ImageField(
        'Изображение',
        upload_to='products/'
    )

    is_main = models.BooleanField(
        'Главное изображение',
        default=False
    )

    order = models.PositiveIntegerField(
        'Порядок сортировки',
        default=0
    )

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'

        ordering = ['order']

        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['is_main']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=Q(is_main=True),
                name='unique_main_product_image'
            )
        ]

    def clean(self):

        super().clean()

        if not self.is_main:
            return

        # Товар еще не сохранен
        if not self.product_id:
            return

        exists = (
            ProductImage.objects
            .filter(
                product_id=self.product_id,
                is_main=True
            )
            .exclude(pk=self.pk)
            .exists()
        )

        if exists:
            raise ValidationError(
                'Главное изображение уже существует'
            )

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(
            *args,
            **kwargs
        )

    def __str__(self):
        return (
            f'Изображение товара '
            f'{self.product.name}'
        )