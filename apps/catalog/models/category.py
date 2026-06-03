from django.db import models
from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel
from django.core.exceptions import ValidationError

# ==========================================================
# КАТЕГОРИИ
# ==========================================================

class Category(BaseModel):

    name = models.CharField(
        'Название',
        max_length=200,
        db_index=True
    )

    slug = models.SlugField(
        'Слаг',
        unique=True,
        blank=True,
        null=True,
        db_index=True
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    meta_title = models.CharField(
        max_length=255,
        blank=True
    )

    meta_description = models.TextField(
        blank=True
    )

    path = models.CharField(
        max_length=1000,
        editable=False,
        db_index=True
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ('name',)

        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def full_name(self):

        names = [self.name]

        parent = self.parent

        while parent:
            names.append(parent.name)

            parent = parent.parent

        return " → ".join(reversed(names))

    def clean(self):
        parent = self.parent
        while parent:
            if parent == self:
                raise ValidationError(
                    'Категория не может быть родителем самой себе'
                )
            parent = parent.parent

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                self.name
            )

        super().save(*args, **kwargs)

        if self.parent:
            self.path = (
                f'{self.parent.path}/{self.slug}'
            )
        else:
            self.path = self.slug

        Category.objects.filter(
            pk=self.pk
        ).update(
            path=self.path
        )

