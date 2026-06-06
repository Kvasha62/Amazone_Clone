from django.db import models
from apps.core.models import BaseModel
from apps.catalog.services.slug_service import generate_unique_slug
from django.core.validators import MinValueValidator

# ==========================================================
# ВАРИАНТ ТОВАРА
# ==========================================================

class ProductVariant(BaseModel):

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Товар'
    )

    sku = models.CharField(
        'Артикул (SKU)',
        max_length=100,
        unique=True,
        db_index=True,
    )

    barcode = models.CharField(
        'Штрихкод',
        max_length=100,
        blank=True,
        db_index=True
    )

    is_active = models.BooleanField(
        'Активен',
        default=True,
        db_index=True
    )

    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    weight = models.DecimalField(
        verbose_name='Вес',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    slug = models.SlugField(
        'Слаг',
        max_length=220,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Вариант товара'
        verbose_name_plural = 'Варианты товара'


    def __str__(self):
        return self.sku

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = generate_unique_slug(
                self,
                f'{self.product.name}-{self.sku}'
            )

        super().save(*args, **kwargs)