# ==============================================================================
# apps/catalog/models/tag.py — Тег товара
# ==============================================================================
# Тег — плоская метка для фильтрации и навигации.
# Примеры: «беспроводные», «водонепроницаемые», «новинка», «хит продаж».
#
# Отличие от Attribute:
#   Tag       = бинарная принадлежность: товар ЛИБО «хит», ЛИБО нет.
#   Attribute = параметр со значением: «цвет = красный», «размер = XL».
#
# M2M-связь: Product.tags ↔ Tag.products
#   Один тег может быть у тысяч товаров.
#   Один товар может иметь десятки тегов.
# ==============================================================================

from django.db import models

from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel


class Tag(BaseModel):
    """
    Тег товара для фильтрации и навигации.

    Примеры: «беспроводные», «водонепроницаемые», «новинка», «хит».
    M2M-связь с Product через tags field.

    Отличие от Attribute:
      - Tag = плоская метка, без значений (бинарная принадлежность).
      - Attribute = параметр с конкретным значением (цвет=красный).
    """

    name = models.CharField(
        'Название',
        max_length=100,
        unique=True,               # unique уже создаёт индекс
    )

    slug = models.SlugField(
        'Слаг',
        max_length=100,
        unique=True,
        blank=True,
    )

    # db_index — теги часто фильтруются: Tag.objects.filter(is_active=True)
    is_active = models.BooleanField(
        'Активен',
        default=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)  # Алфавитный порядок для UI-фильтров

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Slug генерируется один раз при создании (как у Brand).
        # При переименовании slug не меняется — стабильность URL.
        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                field_value=self.name,
            )
        super().save(*args, **kwargs)
