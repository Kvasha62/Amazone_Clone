# ==============================================================================
# apps/catalog/models/variant_attribute.py — Связь варианта со значением атрибута
# ==============================================================================
# Это «E» в EAV (Entity-Attribute-Value):
#   Entity    = ProductVariant (вариант товара)
#   Attribute = Attribute (какая характеристика)
#   Value     = AttributeValue (конкретное значение)
#
# Пример записи:
#   variant = «iPhone 15 Pro 256GB»
#   attribute = «Цвет»
#   value = «Титановый»
#
# Инварианты:
#   1. У варианта — ровно ОДНО значение каждого атрибута.
#      (UniqueConstraint variant + attribute)
#   2. value.attribute_id == attribute_id
#      (нельзя писать VariantAttribute(color_attr, size_value))
# ==============================================================================

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class VariantAttribute(BaseModel):
    """
    Связь варианта товара с конкретным значением атрибута (EAV).

    Пример:
        ProductVariant «iPhone 15 Pro 256GB»
          ├─ VariantAttribute: Цвет = «Титановый»
          ├─ VariantAttribute: Память = «256 GB»
          └─ VariantAttribute: Экран = «6.1\"»
    """

    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,      # Вариант удалён → связи удалены
        related_name='attributes',     # variant.attributes.all()
        verbose_name='Вариант товара',
    )

    attribute = models.ForeignKey(
        'catalog.Attribute',
        on_delete=models.CASCADE,      # Атрибут удалён → связи удалены
        related_name='variant_attributes',
        verbose_name='Атрибут',
    )

    value = models.ForeignKey(
        'catalog.AttributeValue',
        on_delete=models.CASCADE,      # Значение удалено → связи удалены
        related_name='variant_attributes',
        verbose_name='Значение',
    )

    class Meta:
        verbose_name = 'Атрибут варианта'
        verbose_name_plural = 'Атрибуты вариантов'
        ordering = ('attribute__name',)

        indexes = [
            # ----------------------------------------------------------
            # Для фасетного поиска: «найти варианты где атрибут X = Y».
            # Типичный запрос в каталоге при фильтрации по характеристикам.
            # Без индекса — Full Scan на таблице variant_attributes.
            # ----------------------------------------------------------
            models.Index(
                fields=['attribute', 'value'],
                name='variantattr_attr_value_idx',
            ),
        ]

        constraints = [
            # ----------------------------------------------------------
            # Один атрибут — одно значение на вариант.
            # Нельзя: variant=1, attribute=«Цвет», value=«Красный»
            #         variant=1, attribute=«Цвет», value=«Синий»
            # ----------------------------------------------------------
            models.UniqueConstraint(
                fields=['variant', 'attribute'],
                name='unique_variant_attribute',
            ),
        ]

    def __str__(self) -> str:
        # Безопасно: если связи не загружены — fallback на PK
        attr = getattr(self.attribute, 'name', None) or f'#{self.attribute_id}'
        val = getattr(self.value, 'value', None) or f'#{self.value_id}'
        return f'{attr} = {val}'

    def clean(self):
        """
        value.attribute_id должен совпадать с attribute_id.

        Защита от ошибки:
            VariantAttribute(attribute=Цвет, value=XL_размер)
        XL принадлежит атрибуту «Размер», а не «Цвет».
        """
        super().clean()
        if (
            self.attribute_id
            and self.value_id
            and self.value.attribute_id != self.attribute_id
        ):
            raise ValidationError(
                'Значение не принадлежит выбранному атрибуту.',
            )
