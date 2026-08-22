# ────────────────────────────────────────────────────────────────────────
# apps/reviews/serializers/review_serializers.py
#
# СЕРИАЛИЗАТОРЫ ОТЗЫВОВ:
#   CreateReviewInputSerializer — POST (создание)
#   UpdateReviewInputSerializer — PATCH (обновление)
#   HelpfulVoteSerializer       — POST /{id}/helpful/ (голос)
#   ReviewListSerializer        — краткий отзыв (список)
#   ReviewSerializer            — полный отзыв (детали)
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
        help_text='ID товара (числовой PK).',
        required=False,
    )
    # 🔴 product_uuid — для React-фронтенда (фронтенд знает только UUID)
    product_uuid = serializers.UUIDField(
        help_text='UUID товара (альтернатива product_id).',
        required=False,
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

    def validate(self, data):
        """Хотя бы один идентификатор товара обязателен."""
        if not data.get('product_id') and not data.get('product_uuid'):
            raise serializers.ValidationError(
                'Укажите product_id или product_uuid.',
            )
        return data


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


class HelpfulVoteSerializer(serializers.Serializer):
    """POST /api/v1/reviews/{id}/helpful/"""

    vote = serializers.ChoiceField(
        choices=['yes', 'no'],
        help_text='"yes" = полезно, "no" = неполезно.',
    )


# ==============================================================
# OUTPUT
# ==============================================================

class ReviewListSerializer(serializers.ModelSerializer):
    """Краткий отзыв для списка (пагинированный)."""

    user_email = serializers.CharField(
        source='user.email', read_only=True,
    )
    helpful_score = serializers.IntegerField(read_only=True)
    # my_vote заполняется в view ('yes'/'no'/None)
    my_vote = serializers.CharField(
        read_only=True,
        default=None,
        allow_null=True,
    )

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
            'my_vote',
            'created_at',
        )
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    """Полный отзыв с текстом."""

    user_email = serializers.CharField(
        source='user.email', read_only=True,
    )
    helpful_score = serializers.IntegerField(read_only=True)
    # my_vote заполняется в view ('yes'/'no'/None)
    my_vote = serializers.CharField(
        read_only=True,
        default=None,
        allow_null=True,
    )

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
            'my_vote',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields
