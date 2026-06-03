from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import BaseModel

# ==========================================================
# СВЯЗЬ ВАРИАНТА И АТРИБУТОВ
# ==========================================================

class VariantAttribute(BaseModel):
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='attributes',
        verbose_name='Вариант товара'
    )

    attribute = models.ForeignKey(
        'catalog.Attribute',
        on_delete=models.CASCADE,
        verbose_name='Атрибут'
    )

    value = models.ForeignKey(
        'catalog.AttributeValue',
        on_delete=models.CASCADE,
        verbose_name='Значение'
    )

    class Meta:
        verbose_name = 'Атрибут варианта'
        verbose_name_plural = 'Атрибуты вариантов'

        indexes = [
            models.Index(
                fields=['variant']
            ),

            models.Index(
                fields=['attribute']
            ),
            models.Index(
                fields=[
                    'attribute',
                    'value'
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['variant', 'attribute'],
                name='unique_variant_attribute'
            )
        ]

    def clean(self):
        if self.value.attribute_id != self.attribute_id:
            raise ValidationError(
                'Значение не принадлежит атрибуту'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.variant} | {self.attribute} = {self.value.value}'