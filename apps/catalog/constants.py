# ==============================================================================
# apps/catalog/constants.py — Статусы товара
# ==============================================================================
# TextChoices — Django-аналог Python Enum, но с поддержкой:
#   - choices=models.TextChoices.choices в CharField
#   - get_FOO_display() для человекочитаемого текста
#   - migrations: значение хранится как строка (не int),
#     что читаемо в БД: 'active' вместо 1.
#
# Почему TextChoices, а не IntegerChoices:
#   Строковые значения самодокументируемы в БД.
#   SELECT * FROM products WHERE status = 'active' — очевидно.
#   SELECT * FROM products WHERE status = 1 — нужен комментарий.
# ==============================================================================

from django.db import models


class ProductStatus(models.TextChoices):
    """
    Жизненный цикл товара.

    DRAFT        — черновик, виден только менеджеру в admin
    ACTIVE       — опубликован, виден в каталоге
    OUT_OF_STOCK — активен, но показывается «нет в наличии»
    ARCHIVED     — скрыт навсегда (снято с производства)

    Переходы:
        DRAFT → ACTIVE → OUT_OF_STOCK → ARCHIVED
    """

    DRAFT = 'draft', 'Черновик'
    ACTIVE = 'active', 'Активен'
    OUT_OF_STOCK = 'out_of_stock', 'Нет в наличии'
    ARCHIVED = 'archived', 'Архив'

    @property
    def is_visible_in_catalog(self) -> bool:
        """
        Быстрая проверка: показывать ли товар в публичном каталоге.
        Только ACTIVE-товары видны покупателям.
        """
        return self == ProductStatus.ACTIVE
