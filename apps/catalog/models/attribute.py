from django.db import models
from apps.core.models import BaseModel
from apps.catalog.services.slug_service import generate_unique_slug

# ==========================================================
# АТРИБУТЫ
# ==========================================================

class Attribute(BaseModel):

    name = models.CharField(
        'Название',
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        unique=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Атрибут'
        verbose_name_plural = 'Атрибуты'

        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                self.name
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
