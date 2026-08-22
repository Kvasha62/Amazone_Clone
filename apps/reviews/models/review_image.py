# ────────────────────────────────────────────────────────────────────────
# apps/reviews/models/review_image.py — фотография к отзыву.
#
# Аналог ProductImage из catalog, но для отзывов.
# Пользователь может прикрепить до MAX_REVIEW_IMAGES фотографий.
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.core.models.base_model import BaseModel
from apps.reviews.constants import MAX_REVIEW_IMAGES


class ReviewImage(BaseModel):
    """
    Фотография, прикреплённая к отзыву.
    """

    review = models.ForeignKey(
        'reviews.Review',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Отзыв',
    )

    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='reviews/%Y/%m/',
    )

    alt_text = models.CharField(
        verbose_name='Alt-текст',
        max_length=200,
        blank=True,
        default='',
    )

    # Порядок сортировки (1 = первое изображение)
    sort_order = models.PositiveSmallIntegerField(
        verbose_name='Порядок',
        default=0,
    )

    class Meta:
        verbose_name = 'Фото к отзыву'
        verbose_name_plural = 'Фото к отзывам'
        ordering = ('sort_order', 'created_at')

    def __str__(self):
        return f'Фото #{self.pk} к отзыву {self.review_id}'
