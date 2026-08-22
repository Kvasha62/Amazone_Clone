# ────────────────────────────────────────────────────────────────────────
# apps/reviews/querysets/review_queryset.py
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.reviews.constants import MIN_RATING


class ReviewQuerySet(models.QuerySet):
    """Chainable-методы фильтрации для Review."""

    def approved(self):
        """Только одобренные отзывы."""
        return self.filter(is_approved=True)

    def pending(self):
        """Отзывы, ожидающие модерации."""
        return self.filter(is_approved=False)

    def for_product(self, product):
        """Отзывы на конкретный товар."""
        return self.filter(product=product)

    def for_product_id(self, product_id: int):
        """Отзывы на товар по ID."""
        return self.filter(product_id=product_id)

    def for_user(self, user):
        """Отзывы конкретного пользователя."""
        return self.filter(user=user)

    def for_user_id(self, user_id: int):
        """Отзывы пользователя по ID."""
        return self.filter(user_id=user_id)

    def verified(self):
        """Только отзывы с подтверждённой покупкой."""
        return self.filter(verified_purchase=True)

    def with_rating(self, rating: int):
        """Фильтр по конкретному рейтингу."""
        return self.filter(rating=rating)

    def high_rated(self):
        """Рейтинг 4-5 (положительные)."""
        return self.filter(rating__gte=4)

    def low_rated(self):
        """Рейтинг 1-2 (отрицательные)."""
        return self.filter(rating__lte=2)

    def with_user(self):
        """select_related user."""
        return self.select_related('user')

    def with_product(self):
        """select_related product."""
        return self.select_related('product')

    def with_images(self):
        """prefetch_related images."""
        return self.prefetch_related('images')
