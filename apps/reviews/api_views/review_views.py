# ────────────────────────────────────────────────────────────────────────
# apps/reviews/api_views/review_views.py
#
# ЭНДПОИНТЫ:
#   GET/POST  /api/v1/reviews/           — список / создание
#   GET/PATCH /api/v1/reviews/{id}/      — детали / обновление
#   DELETE    /api/v1/reviews/{id}/      — удаление
# ────────────────────────────────────────────────────────────────────────

import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.reviews.models import Review
from apps.reviews.serializers import (
    CreateReviewInputSerializer,
    ReviewListSerializer,
    ReviewSerializer,
    UpdateReviewInputSerializer,
)
from apps.reviews.services.review_service import ReviewService

try:
    from drf_spectacular.utils import extend_schema, extend_schema_view
except ImportError:
    def extend_schema(**kwargs):
        def decorator(func):
            return func
        return decorator

    def extend_schema_view(**kwargs):
        def decorator(cls):
            return cls
        return decorator

logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary='Список отзывов',
        description='Возвращает отзывы. Фильтрация: ?product_id=&user_id=',
        responses={200: ReviewListSerializer(many=True)},
    ),
    post=extend_schema(
        summary='Создать отзыв',
        request=CreateReviewInputSerializer,
        responses={201: ReviewSerializer},
    ),
)
class ReviewListView(APIView):
    """GET/POST /api/v1/reviews/"""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        GET /api/v1/reviews/

        Query params:
          ?product_id=1  — отзывы на товар
          ?user_id=2     — отзывы пользователя (staff only)
        """
        qs = Review.objects.approved().with_user()

        product_id = request.query_params.get('product_id')
        if product_id:
            qs = qs.for_product_id(int(product_id))

        user_id = request.query_params.get('user_id')
        if user_id:
            if not request.user.is_staff and int(user_id) != request.user.pk:
                # Не-staff может видеть только свои отзывы
                user_id = request.user.pk
            qs = qs.for_user_id(int(user_id))

        # По умолчанию — отзывы текущего пользователя
        if not product_id and not user_id:
            qs = qs.for_user(request.user)

        serializer = ReviewListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        """POST /api/v1/reviews/"""
        input_ser = CreateReviewInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        try:
            product = Product.objects.get(pk=data['product_id'])
        except Product.DoesNotExist:
            raise NotFound('Товар не найден.')

        review = ReviewService.create_review(
            user=request.user,
            product=product,
            rating=data['rating'],
            text=data['text'],
            title=data.get('title', ''),
        )

        return Response(
            ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        summary='Детали отзыва',
        responses={200: ReviewSerializer},
    ),
    patch=extend_schema(
        summary='Обновить отзыв',
        request=UpdateReviewInputSerializer,
        responses={200: ReviewSerializer},
    ),
    delete=extend_schema(
        summary='Удалить отзыв',
        responses={204: None},
    ),
)
class ReviewDetailView(APIView):
    """GET/PATCH/DELETE /api/v1/reviews/{id}/"""

    permission_classes = (IsAuthenticated,)

    def _get_review(self, request, review_id: int) -> Review:
        try:
            review = Review.objects.select_related('user', 'product').get(pk=review_id)
        except Review.DoesNotExist:
            raise NotFound('Отзыв не найден.')

        # Не-staff видит только свои или одобренные
        if not request.user.is_staff:
            if review.user_id != request.user.pk and not review.is_approved:
                raise NotFound('Отзыв не найден.')

        return review

    def get(self, request, review_id: int):
        review = self._get_review(request, review_id)
        return Response(ReviewSerializer(review).data)

    def patch(self, request, review_id: int):
        review = self._get_review(request, review_id)

        input_ser = UpdateReviewInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)

        review = ReviewService.update_review(
            review,
            user=request.user,
            **input_ser.validated_data,
        )
        return Response(ReviewSerializer(review).data)

    def delete(self, request, review_id: int):
        review = self._get_review(request, review_id)
        ReviewService.delete_review(review, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
