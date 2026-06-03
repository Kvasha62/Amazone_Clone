from django.db import models
# from services.slug_service import generate_unique_slug
from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel

# ==========================================================
# БРЕНДЫ
# ==========================================================

class Brand(BaseModel):

    name = models.CharField(
        'Название',
        max_length=100,
        unique=True,
        db_index=True,
    )

    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=255,
        unique=True,
        blank=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                self.name
            )

        super().save(*args, **kwargs)
