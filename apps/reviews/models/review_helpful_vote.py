# ────────────────────────────────────────────────────────────────────────
# apps/reviews/models/review_helpful_vote.py — голос за полезность отзыва.
#
# БИЗНЕС-ПРАВИЛА:
#   • Один пользователь — один голос на отзыв (UniqueConstraint)
#   • vote='yes' → полезно, vote='no' → неполезно
#   • Повторный голос с тем же значением → отмена (toggle off)
#   • Повторный голос с другим значением → переключение (yes→no или no→yes)
#   • При создании/удалении/переключении пересчитываются
#     Review.helpful_yes и Review.helpful_no
#
# АНАЛОГ: Amazon «Helpful» / «Not Helpful» на отзывах.
# ────────────────────────────────────────────────────────────────────────

from django.conf import settings
from django.db import models

from apps.core.models.base_model import BaseModel


class ReviewHelpfulVote(BaseModel):
    """
    Голос пользователя за полезность отзыва.

    СВЯЗИ:
      • User (FK) — кто голосовал
      • Review (FK) — за какой отзыв

    ЛОГИКА (в ReviewService.vote_helpful):
      1. Если пользователь ещё не голосовал → создаём голос
      2. Если тот же голос повторно → удаляем (toggle off)
      3. Если другой голос → обновляем (yes→no или no→yes)
    """

    VOTE_YES = 'yes'
    VOTE_NO = 'no'
    VOTE_CHOICES = [
        (VOTE_YES, 'Полезно'),
        (VOTE_NO, 'Неполезно'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_helpful_votes',
        verbose_name='Пользователь',
    )

    review = models.ForeignKey(
        'reviews.Review',
        on_delete=models.CASCADE,
        related_name='helpful_votes',
        verbose_name='Отзыв',
    )

    vote = models.CharField(
        max_length=3,
        choices=VOTE_CHOICES,
        verbose_name='Голос',
    )

    class Meta:
        verbose_name = 'Голос за отзыв'
        verbose_name_plural = 'Голоса за отзывы'
        constraints = [
            # Один голос на отзыв от одного пользователя.
            models.UniqueConstraint(
                fields=['user', 'review'],
                name='unique_user_review_helpful_vote',
            ),
        ]
        indexes = [
            models.Index(
                fields=['review', 'vote'],
                name='review_vote_idx',
            ),
        ]

    def __str__(self):
        return f'{self.user_id} → {self.vote} на отзыв {self.review_id}'
