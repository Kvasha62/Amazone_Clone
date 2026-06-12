# ────────────────────────────────────────────────────────────────────────
# apps/reviews/models/review.py — модель отзыва на товар.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Пользователь оставляет отзыв (текст + рейтинг 1-5) на товар
#   • Один отзыв на товар от одного пользователя (UniqueConstraint)
#   • verified_purchase=True если пользователь купил этот товар
#   • Лайки (helpful_yes) / дизлайки (helpful_no) на отзыв
#   • Модерация: is_approved (False → не виден в каталоге)
#
# ДЕНОРМАЛИЗАЦИЯ:
#   Product.rating и Product.reviews_count автоматически обновляются
#   через сигнал при создании/удалении/изменении отзыва.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/
# ────────────────────────────────────────────────────────────────────────

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.reviews.constants import MAX_RATING, MIN_RATING, MAX_REVIEW_TEXT_LENGTH
from apps.reviews.managers.review_manager import ReviewManager


class Review(BaseModel):
    """
    Отзыв пользователя на товар.

    СВЯЗИ:
      • User (FK) — автор отзыва
      • Product (FK) — товар, на который написан отзыв
      • ReviewImage (reverse FK) — фотографии к отзыву
    """

    objects = ReviewManager()

    # ── Автор ──
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Автор',
    )

    # ── Товар ──
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар',
    )

    # ── Рейтинг (1-5 звёзд) ──
    rating = models.PositiveSmallIntegerField(
        verbose_name='Рейтинг',
        validators=[
            MinValueValidator(MIN_RATING),
            MaxValueValidator(MAX_RATING),
        ],
        db_index=True,
    )

    # ── Текст отзыва ──
    title = models.CharField(
        verbose_name='Заголовок',
        max_length=200,
        blank=True,
        default='',
    )
    text = models.TextField(
        verbose_name='Текст отзыва',
        max_length=MAX_REVIEW_TEXT_LENGTH,
    )

    # ── Подтверждённая покупка ──
    # True если пользователь реально купил этот товар (по OrderItem).
    verified_purchase = models.BooleanField(
        verbose_name='Подтверждённая покупка',
        default=False,
        db_index=True,
    )

    # ── Модерация ──
    is_approved = models.BooleanField(
        verbose_name='Одобрен',
        default=True,
        db_index=True,
        help_text='False = скрыт до модерации.',
    )

    # ── Полезность отзыва (лайки/дизлайки) ──
    helpful_yes = models.PositiveIntegerField(
        verbose_name='Полезно',
        default=0,
    )
    helpful_no = models.PositiveIntegerField(
        verbose_name='Неполезно',
        default=0,
    )

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('-created_at',)
        constraints = [
            # Один отзыв на товар от одного пользователя.
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_review',
            ),
        ]
        indexes = [
            # Индекс для listing: «одобренные отзывы товара, по дате»
            models.Index(
                fields=['product', 'is_approved', '-created_at'],
                name='review_product_approved_idx',
            ),
            # Индекс для аналитики: «все отзывы пользователя»
            models.Index(
                fields=['user', '-created_at'],
                name='review_user_created_idx',
            ),
        ]

    def __str__(self):
        return (
            f'★{self.rating} от {getattr(self.user, "email", "?")} '
            f'на {getattr(self.product, "name", "?")}'
        )

    @property
    def helpful_score(self) -> int:
        """Разница лайков/дизлайков: helpful_yes - helpful_no."""
        return self.helpful_yes - self.helpful_no
