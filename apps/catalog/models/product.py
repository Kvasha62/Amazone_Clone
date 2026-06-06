from django.db import models

from apps.core.models import BaseModel
from apps.catalog.services.slug_service import generate_unique_slug
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)
from apps.catalog.managers.product_manager import ProductManager

# ==========================================================
# ТОВАР
# ==========================================================

class Product(BaseModel):
    objects = ProductManager()
    name = models.CharField(
        verbose_name='Название',
        max_length=255,
        db_index=True
    )

    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=255,
        unique=True,
        db_index=True,
        blank=True
    )

    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )

    meta_title = models.CharField(
        max_length=255,
        blank=True
    )

    meta_description = models.TextField(
        blank=True
    )

    manufacturer_code = models.CharField(
        max_length=100,
        blank=True,
        db_index=True
    )

    brand = models.ForeignKey(
        'catalog.Brand',
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Бренд'
    )

    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория'
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5)
        ],
        db_index=True
    )

    reviews_count = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

        ordering = ('name',)

        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                field_value=self.name
            )

        super().save(*args, **kwargs)