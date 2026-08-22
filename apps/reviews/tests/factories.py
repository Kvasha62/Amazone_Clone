# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/factories.py
# ────────────────────────────────────────────────────────────────────────

from apps.reviews.models import Review


def create_test_review(user, product, **kwargs):
    """Создаёт тестовый отзыв."""
    defaults = {
        'rating': kwargs.pop('rating', 5),
        'title': kwargs.pop('title', 'Отличный товар'),
        'text': kwargs.pop('text', 'Очень понравился, рекомендую всем!'),
        'verified_purchase': kwargs.pop('verified_purchase', False),
        'is_approved': kwargs.pop('is_approved', True),
    }
    defaults.update(kwargs)
    return Review.objects.create(user=user, product=product, **defaults)
