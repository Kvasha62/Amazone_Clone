# ────────────────────────────────────────────────────────────────────────
# apps/reviews/serializers/review_serializers.py
# ────────────────────────────────────────────────────────────────────────

from rest_framework import serializers

from apps.reviews.constants import (
    MAX_RATING,
    MIN_RATING,
    MAX_REVIEW_TEXT_LENGTH,
    MIN_REVIEW_TEXT_LENGTH,
)
from apps.reviews.models import Review


# ==============================================================
# INPUT
# ==============================================================

class CreateReviewInputSerializer(serializers.Serializer):
    """POST /api/v1/reviews/"""

    product_id = serializers.IntegerField(
        help_text='ID товара.',
    )
    rating = serializers.IntegerField(
        min_value=MIN_RATING,
        max_value=MAX_RATING,
        help_text=f'Рейтинг от {MIN_RATING} до {MAX_RATING}.',
    )
    title = serializers.CharField(
        max_length=200,
        required=False,
        default='',
        allow_blank=True,
    )
    text = serializers.CharField(
        max_length=MAX_REVIEW_TEXT_LENGTH,
        min_length=MIN_REVIEW_TEXT_LENGTH,
        help_text=f'От {MIN_REVIEW_TEXT_LENGTH} до {MAX_REVIEW_TEXT_LENGTH} символов.',
    )


class UpdateReviewInputSerializer(serializers.Serializer):
    """PATCH /api/v1/reviews/{id}/"""

    rating = serializers.IntegerField(
        min_value=MIN_RATING,
        max_value=MAX_RATING,
        required=False,
    )
    title = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
    )
    text = serializers.CharField(
        max_length=MAX_REVIEW_TEXT_LENGTH,
        min_length=MIN_REVIEW_TEXT_LENGTH,
        required=False,
    )


# ==============================================================
# OUTPUT
# ==============================================================

class ReviewListSerializer(serializers.ModelSerializer):
    """Краткий отзыв для списка."""

    user_email = serializers.CharField(
        source='user.email', read_only=True,
    )
    helpful_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Review
        fields = (
            'id',
            'user_id',
            'user_email',
            'product_id',
            'rating',
            'title',
            'verified_purchase',
            'helpful_yes',
            'helpful_no',
            'helpful_score',
            'created_at',
        )
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    """Полный отзыв с текстом."""

    user_email = serializers.CharField(
        source='user.email', read_only=True,
    )
    helpful_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Review
        fields = (
            'id',
            'user_id',
            'user_email',
            'product_id',
            'rating',
            'title',
            'text',
            'verified_purchase',
            'is_approved',
            'helpful_yes',
            'helpful_no',
            'helpful_score',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields
