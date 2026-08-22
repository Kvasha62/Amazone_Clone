# ==============================================================================
# apps/catalog/models/attribute_value.py — Допустимое значение атрибута
# ==============================================================================
# Пример: Attribute «Цвет» → AttributeValue «Красный», «Синий», «Зелёный».
#
# Зачем отдельная модель (а не просто CharField на VariantAttribute):
#   1. Нормализация — «Красный» хранится один раз, ссылаются 1000 товаров.
#   2. UniqueConstraint(attribute, value) — нельзя создать дубликат.
#   3. color_hex — визуальное представление в UI (красный кружок → #FF0000).
#   4. Фасетный поиск — «сколько товаров с Цвет=Красный» — простой COUNT.
# ==============================================================================

from django.db import models

from apps.core.models import BaseModel


class AttributeValue(BaseModel):
    """
    Допустимое значение атрибута.

    Принадлежит конкретному Attribute — гарантируется на уровне БД
    через UniqueConstraint(attribute, value) и в clean().

    Пример:
        Attribute «Цвет» → AttributeValue «Красный», «Синий»
    """

    # ------------------------------------------------------------------
    # FK к Attribute — «какому атрибуту принадлежит это значение?»
    # ------------------------------------------------------------------
    # on_delete=CASCADE — если удалим атрибут «Цвет»,
    #   все его значения «Красный», «Синий» тоже удалятся.
    # related_name='values' — обращение: attribute.values.all()
    # ------------------------------------------------------------------
    attribute = models.ForeignKey(
        'catalog.Attribute',
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name='Атрибут',
    )

    # ------------------------------------------------------------------
    # value — текстовое значение («Красный», «XL», «256 GB»)
    # ------------------------------------------------------------------
    # НЕ unique глобально — «Красный» может быть у «Цвет» и у «Отделка».
    # Уникальность — в составе (attribute, value) через UniqueConstraint.
    # ------------------------------------------------------------------
    value = models.CharField(
        'Значение',
        max_length=100,
    )

    # ------------------------------------------------------------------
    # color_hex — HEX-цвет для UI-фильтров
    # ------------------------------------------------------------------
    # Опционально: только для цветных атрибутов.
    # Валидируется в clean() — формат #RRGGBB.
    # ------------------------------------------------------------------
    color_hex = models.CharField(
        'HEX-цвет',
        max_length=7,
        blank=True,
        help_text='Для цветных атрибутов: #FF0000, #0000FF и т.д.',
    )

    class Meta:
        verbose_name = 'Значение атрибута'
        verbose_name_plural = 'Значения атрибутов'
        # Группировка по атрибуту, внутри — по алфавиту значений
        ordering = ('attribute__name', 'value')

        constraints = [
            # ----------------------------------------------------------
            # Составная уникальность: у атрибута «Цвет» не может быть
            # двух значений «Красный». PostgreSQL создаёт partial index.
            # ----------------------------------------------------------
            models.UniqueConstraint(
                fields=['attribute', 'value'],
                name='unique_attribute_value',
            ),
        ]

    def __str__(self) -> str:
        # ----------------------------------------------------------
        # Безопасный __str__ — избегаем N+1:
        # Если attribute не загружен (нет select_related),
        # getattr вернёт None вместо бросания исключения.
        # Fallback на PK — лучше чем crash в логах.
        # ----------------------------------------------------------
        attr_name = getattr(self.attribute, 'name', None)
        if attr_name:
            return f'{attr_name}: {self.value}'
        return f'#{self.attribute_id}: {self.value}'

    def clean(self):
        """
        Валидация color_hex — если указан, должен быть #RRGGBB.
        """
        super().clean()
        if self.color_hex:
            import re
            # re.search с ^ вместо re.match — совместимость с Python 3.15+
            # (re.match «softly deprecated» в 3.15 в пользу prefixmatch)
            if not re.search(r'^#[0-9A-Fa-f]{6}$', self.color_hex):
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'color_hex': 'Формат: #RRGGBB (например, #FF0000).',
                })
