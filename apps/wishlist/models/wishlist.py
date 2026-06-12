# ────────────────────────────────────────────────────────────────────────
# apps/wishlist/models/wishlist.py — список желаний (Wishlist).
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Один список желаний на пользователя (OneToOne)
#   • Автосоздание при первом добавлении товара
#   • items_count (denormalized) — количество товаров
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/
# ────────────────────────────────────────────────────────────────────────

from django.conf import settings
from django.db import models

from apps.core.models.base_model import BaseModel


class Wishlist(BaseModel):
    """
    Список желаний пользователя.

    OneToOne к User — у каждого пользователя ровно один список.
    Создаётся автоматически при первом добавлении товара
    (WishlistService.get_or_create).

    СВЯЗИ:
      • User (OneToOne) — владелец списка
      • WishlistItem (reverse FK) — товары в списке
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name='Пользователь',
    )

    # Denormalized: количество товаров.
    # Обновляется в WishlistService.add_item/remove_item/clear.
    items_count = models.PositiveIntegerField(
        verbose_name='Количество товаров',
        default=0,
    )

    class Meta:
        verbose_name = 'Список желаний'
        verbose_name_plural = 'Списки желаний'

    def __str__(self):
        return f'Wishlist({self.user_id}, {self.items_count} items)'
