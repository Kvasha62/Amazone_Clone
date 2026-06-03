from django.db import models
from apps.core.models import BaseModel

class AttributeValue(BaseModel):

    attribute = models.ForeignKey(
        'catalog.Attribute',
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name='Атрибут'
    )

    value = models.CharField(
        'Значение',
        max_length=100,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Значение атрибута'
        verbose_name_plural = 'Значения атрибутов'

        constraints = [
            models.UniqueConstraint(
                fields=['attribute', 'value'],
                name='unique_attribute_value'
            )
        ]

    def __str__(self):
        return f'{self.attribute.name}: {self.value}'