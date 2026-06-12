# ────────────────────────────────────────────────────────────────────────
# apps/discounts/models/campaign.py — рекламная кампания скидок.
#
# Кампания группирует несколько купонов:
#   «Чёрная пятница» → купоны BF10, BF20, BF50
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.core.models.base_model import BaseModel
from apps.discounts.constants import CAMPAIGN_NUMBER_DIGITS, CAMPAIGN_PREFIX


class Campaign(BaseModel):
    """
    Рекламная кампания (группировка купонов).
    """
    name = models.CharField(
        verbose_name='Название кампании',
        max_length=200,
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        default='',
    )

    is_active = models.BooleanField(
        verbose_name='Активна',
        default=True,
        db_index=True,
    )

    started_at = models.DateTimeField(
        verbose_name='Дата начала',
        db_index=True,
    )
    ended_at = models.DateTimeField(
        verbose_name='Дата окончания',
        db_index=True,
    )

    class Meta:
        verbose_name = 'Кампания'
        verbose_name_plural = 'Кампании'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    @property
    def is_running(self) -> bool:
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.started_at <= now <= self.ended_at
