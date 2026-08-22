# ────────────────────────────────────────────────────────────────────────
# apps/reviews/services/review_service.py — бизнес-логика отзывов.
#
# ОПЕРАЦИИ:
#   create_review()    — создать отзыв с проверкой «не уже ли»
#   update_review()    — изменить текст/рейтинг
#   delete_review()    — удалить отзыв
#   approve_review()   — модерация: одобрить
#   reject_review()    — модерация: отклонить
#   recalculate_product_rating() — обновить Product.rating
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging

from django.db import models, transaction
from django.db.models import Avg, Count, Q

from rest_framework.exceptions import NotFound, ValidationError

from apps.reviews.constants import (
    MAX_RATING,
    MIN_RATING,
    MIN_REVIEW_TEXT_LENGTH,
)
from apps.reviews.models import Review

logger = logging.getLogger(__name__)


class ReviewService:
    """Бизнес-логика отзывов."""

    # ==============================================================
    # Создание отзыва
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def create_review(
        user,
        product,
        *,
        rating: int,
        text: str,
        title: str = '',
    ) -> Review:
        """
        Создаёт отзыв на товар.

        ВАЛИДАЦИЯ:
          • Один отзыв на товар от одного пользователя
          • Рейтинг 1-5
          • Текст не короче MIN_REVIEW_TEXT_LENGTH
          • Нельзя оставить отзыв на свой же товар (опционально)

        ПОСЛЕ СОЗДАНИЯ:
          • Пересчитывается Product.rating и Product.reviews_count
          • verified_purchase=True если пользователь покупал товар
        """
        # ── Валидация ──
        if rating < MIN_RATING or rating > MAX_RATING:
            raise ValidationError({
                'rating': f'Рейтинг должен быть от {MIN_RATING} до {MAX_RATING}.',
            })

        if len(text.strip()) < MIN_REVIEW_TEXT_LENGTH:
            raise ValidationError({
                'text': (
                    f'Минимальная длина отзыва — '
                    f'{MIN_REVIEW_TEXT_LENGTH} символов.'
                ),
            })

        # ── Проверка: не оставлял ли уже отзыв ──
        if Review.objects.filter(user=user, product=product).exists():
            raise ValidationError({
                'detail': 'Вы уже оставили отзыв на этот товар.',
            })

        # ── Проверка: купил ли пользователь товар ──
        verified = ReviewService._check_verified_purchase(user, product)

        review = Review.objects.create(
            user=user,
            product=product,
            rating=rating,
            text=text.strip(),
            title=title.strip(),
            verified_purchase=verified,
        )

        # ── Обновляем денормализованный рейтинг товара ──
        ReviewService.recalculate_product_rating(product)

        logger.info(
            'review_created',
            extra={
                'review_id': review.pk,
                'user_id': user.pk,
                'product_id': product.pk,
                'rating': rating,
                'verified': verified,
            },
        )

        return review

    # ==============================================================
    # Обновление отзыва
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def update_review(
        review: Review,
        *,
        user,
        rating: int | None = None,
        text: str | None = None,
        title: str | None = None,
    ) -> Review:
        """
        Обновляет отзыв. Только автор может редактировать.
        """
        if review.user_id != user.pk:
            raise NotFound('Отзыв не найден.')

        changed = False

        if rating is not None:
            if rating < MIN_RATING or rating > MAX_RATING:
                raise ValidationError({
                    'rating': f'Рейтинг от {MIN_RATING} до {MAX_RATING}.',
                })
            review.rating = rating
            changed = True

        if text is not None:
            if len(text.strip()) < MIN_REVIEW_TEXT_LENGTH:
                raise ValidationError({
                    'text': f'Минимум {MIN_REVIEW_TEXT_LENGTH} символов.',
                })
            review.text = text.strip()
            changed = True

        if title is not None:
            review.title = title.strip()
            changed = True

        if changed:
            review.save()
            ReviewService.recalculate_product_rating(review.product)

        return review

    # ==============================================================
    # Удаление отзыва
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def delete_review(review: Review, *, user) -> None:
        """Удаляет отзыв. Автор или staff."""
        if review.user_id != user.pk and not user.is_staff:
            raise NotFound('Отзыв не найден.')

        review_id = review.pk       # 🔴 Сохраняем PK до delete() — потом review.pk=None
        product = review.product
        review.delete()
        ReviewService.recalculate_product_rating(product)

        logger.info(
            'review_deleted',
            extra={
                'review_id': review_id,
                'product_id': product.pk,
                'deleted_by': user.pk,
            },
        )

    # ==============================================================
    # Модерация
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def approve_review(review: Review) -> Review:
        """Одобряет отзыв (модерация)."""
        review.is_approved = True
        review.save(update_fields=['is_approved', 'updated_at'])
        ReviewService.recalculate_product_rating(review.product)
        return review

    @staticmethod
    @transaction.atomic
    def reject_review(review: Review) -> Review:
        """Отклоняет отзыв (модерация)."""
        review.is_approved = False
        review.save(update_fields=['is_approved', 'updated_at'])
        ReviewService.recalculate_product_rating(review.product)
        return review

    # ==============================================================
    # Пересчёт денормализованного рейтинга товара
    # ==============================================================

    @staticmethod
    def recalculate_product_rating(product) -> None:
        """
        Пересчитывает Product.rating и Product.reviews_count
        на основе ВСЕХ одобренных отзывов.

        ВЫЗЫВАЕТСЯ ПРИ:
          • Создании/редактировании/удалении отзыва
          • Модерации (approve/reject)

        АЛГОРИТМ:
          1. Aggregate AVG(rating) + COUNT по одобренным отзывам
          2. Обновить Product.rating и Product.reviews_count
        """
        from decimal import Decimal

        stats = Review.objects.filter(
            product=product,
            is_approved=True,
        ).aggregate(
            avg_rating=Avg('rating'),
            total=Count('id'),
        )

        avg = stats['avg_rating'] or Decimal('0.00')
        total = stats['total'] or 0

        # Округляем до 2 знаков
        avg = round(Decimal(str(avg)), 2)

        product.update_rating(
            new_rating=avg,
            total_reviews=total,
        )

    # ==============================================================
    # Голосование за полезность отзыва
    # ==============================================================

    @staticmethod
    @transaction.atomic
    def vote_helpful(review: Review, *, user, vote: str) -> Review:
        """
        Голосует за полезность отзыва с toggle-логикой.

        АРГУМЕНТЫ:
          user — авторизованный пользователь
          vote='yes' → полезно, vote='no' → неполезно

        ЛОГИКА (как Reddit/Amazon):
          1. Пользователь ещё не голосовал → создаём голос
             → helpful_yes += 1 (или helpful_no += 1)
          2. Тот же голос повторно → удаляем (toggle off)
             → helpful_yes -= 1 (или helpful_no -= 1)
          3. Другой голос → переключаем (yes→no или no→yes)
             → helpful_yes -= 1, helpful_no += 1 (или наоборот)

        ВОЗВРАЩАЕТ:
          Review с обновлёнными helpful_yes / helpful_no.

        ВЫБРАСЫВАЕТ:
          ValidationError — если голос не 'yes'/'no'.
          ValidationError — если автор отзыва голосует за свой же отзыв.
        """
        from apps.reviews.models import ReviewHelpfulVote

        if vote not in (ReviewHelpfulVote.VOTE_YES, ReviewHelpfulVote.VOTE_NO):
            raise ValidationError({'vote': 'Значение должно быть "yes" или "no".'})

        # ── Автор отзыва не может голосовать за свой же отзыв ──
        if review.user_id == user.pk:
            raise ValidationError({
                'detail': 'Нельзя голосовать за свой же отзыв.',
            })

        existing = ReviewHelpfulVote.objects.filter(
            user=user,
            review=review,
        ).select_for_update().first()

        if existing is None:
            # ── Новый голос ──
            ReviewHelpfulVote.objects.create(user=user, review=review, vote=vote)
            if vote == ReviewHelpfulVote.VOTE_YES:
                review.helpful_yes = models.F('helpful_yes') + 1
            else:
                review.helpful_no = models.F('helpful_no') + 1

        elif existing.vote == vote:
            # ── Toggle off: повторный тот же голос → отмена ──
            existing.delete()
            if vote == ReviewHelpfulVote.VOTE_YES:
                review.helpful_yes = models.F('helpful_yes') - 1
            else:
                review.helpful_no = models.F('helpful_no') - 1

        else:
            # ── Переключение: yes→no или no→yes ──
            existing.vote = vote
            existing.save(update_fields=['vote', 'updated_at'])
            if vote == ReviewHelpfulVote.VOTE_YES:
                # Был 'no', стал 'yes'
                review.helpful_yes = models.F('helpful_yes') + 1
                review.helpful_no = models.F('helpful_no') - 1
            else:
                # Был 'yes', стал 'no'
                review.helpful_yes = models.F('helpful_yes') - 1
                review.helpful_no = models.F('helpful_no') + 1

        review.save(update_fields=['helpful_yes', 'helpful_no', 'updated_at'])
        review.refresh_from_db()

        logger.info(
            'review_helpful_vote',
            extra={
                'review_id': review.pk,
                'user_id': user.pk,
                'vote': vote,
                'helpful_yes': review.helpful_yes,
                'helpful_no': review.helpful_no,
            },
        )

        return review

    # ==============================================================
    # Получить голос текущего пользователя для отзыва
    # ==============================================================

    @staticmethod
    def get_user_vote(review: Review, user) -> str | None:
        """
        Возвращает голос пользователя для отзыва:
          'yes' / 'no' / None (не голосовал).
        """
        from apps.reviews.models import ReviewHelpfulVote

        vote_obj = ReviewHelpfulVote.objects.filter(
            user=user,
            review=review,
        ).values_list('vote', flat=True).first()
        return vote_obj

    # ==============================================================
    # Проверка покупки
    # ==============================================================

    @staticmethod
    def _check_verified_purchase(user, product) -> bool:
        """
        True если пользователь купил данный товар
        (есть OrderItem с variant.product == product
        в заказе со статусом CONFIRMED/SHIPPED/DELIVERED).
        """
        from apps.orders.models import OrderItem
        from apps.orders.models.order import OrderStatus

        return OrderItem.objects.filter(
            order__user=user,
            order__status__in=[
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
            ],
            variant__product=product,
        ).exists()
