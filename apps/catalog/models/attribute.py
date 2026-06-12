# ==============================================================================
# apps/catalog/models/attribute.py — Атрибут товара (EAV-паттерн)
# ==============================================================================
# Атрибут — именованная характеристика товара: «Цвет», «Размер», «Материал».
#
# Это часть EAV (Entity-Attribute-Value) паттерна:
#   Entity   = ProductVariant (вариант товара)
#   Attribute = эта модель (название характеристики)
#   Value    = AttributeValue (допустимые значения)
#   Link     = VariantAttribute (связь варианта со значением)
#
# Пример дерева:
#   Attribute «Цвет»
#     ├─ AttributeValue «Красный»
#     ├─ AttributeValue «Синий»
#     └─ AttributeValue «Зелёный»
#
#   ProductVariant «iPhone 128GB»
#     └─ VariantAttribute: Цвет = Красный
#
# Почему EAV, а не JSON-поле:
#   1. Типизация — каждое значение в отдельной строке, валидация на уровне БД.
#   2. Фасетный поиск — «покажи все товары где Цвет=Красный» — простой JOIN.
#   3. Админка — django-admin автоматически показывает dropdown со значениями.
# ==============================================================================

from django.db import models

from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel


class Attribute(BaseModel):
    """
    Характеристика товара: «Цвет», «Размер», «Материал».

    Связь с вариантами через VariantAttribute (EAV-паттерн).
    Связь с возможными значениями через AttributeValue.
    """

    name = models.CharField(
        'Название',
        max_length=100,
        unique=True,               # unique уже создаёт индекс
    )

    slug = models.SlugField(
        'Слаг',
        max_length=100,
        unique=True,               # unique уже создаёт индекс
        blank=True,                # заполняется автоматически в save()
    )

    # description — пояснение для менеджеров в админке:
    #   «Используйте для указания основного цвета обивки»
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Для админки — поясняет, что означает этот атрибут.',
    )

    class Meta:
        verbose_name = 'Атрибут'
        verbose_name_plural = 'Атрибуты'
        ordering = ('name',)  # Алфавитный порядок в UI-фильтрах

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Slug из name — один раз при создании
        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                field_value=self.name,
            )
        super().save(*args, **kwargs)
