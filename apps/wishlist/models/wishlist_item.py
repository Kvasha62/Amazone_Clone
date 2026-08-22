# ────────────────────────────────────────────────────────────────────────
# apps/wishlist/models/wishlist_item.py — позиция в списке желаний.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Один вариант товара — одна позиция (UniqueConstraint)
#   • Заметка пользователя (опционально)
#   • Приоритет сортировки (меньше = выше)
#   • Цена на момент добавления (snapshot)
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.db import models

from apps.core.models.base_model import BaseModel
from apps.wishlist.constants import DEFAULT_SORT_ORDER, MAX_NOTE_LENGTH


class WishlistItem(BaseModel):
    """
    Товар в списке желаний.

    UniqueConstraint(wishlist + variant) — нельзя добавить
    один и тот же вариант дважды.

    СВЯЗИ:
      • Wishlist (FK) — список желаний
      • ProductVariant (FK) — вариант товара
    """

    wishlist = models.ForeignKey(
        'wishlist.Wishlist',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Список желаний',
    )

    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='Вариант товара',
    )

    # Заметка пользователя к товару
    # «Хочу на день рождения», «К лету» и т.д.
    note = models.TextField(
        verbose_name='Заметка',
        blank=True,
        default='',
        max_length=MAX_NOTE_LENGTH,
    )

    # Приоритет сортировки (меньше = выше в списке)
    sort_order = models.PositiveSmallIntegerField(
        verbose_name='Порядок',
        default=DEFAULT_SORT_ORDER,
    )

    class Meta:
        verbose_name = 'Позиция избранного'
        verbose_name_plural = 'Позиции избранного'
        ordering = ('sort_order', '-created_at')
        constraints = [
            models.UniqueConstraint(
                fields=['wishlist', 'variant'],
                name='wishlist_item_unique_variant',
            ),
        ]

    def __str__(self):
        return f'WishlistItem(wishlist={self.wishlist_id}, variant={self.variant_id})'
