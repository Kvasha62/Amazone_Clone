import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductVariant
from apps.wishlist.serializers import (
    AddToWishlistInputSerializer,
    MoveToCartInputSerializer,
    WishlistItemSerializer,
    WishlistSerializer,
)
from apps.wishlist.services.wishlist_service import WishlistService

try:
    from drf_spectacular.utils import extend_schema, extend_schema_view
except ImportError:
    def extend_schema(**kwargs):
        def decorator(func): return func
        return decorator
    def extend_schema_view(**kwargs):
        def decorator(cls): return cls
        return decorator

logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary='Список желаний',
        responses={200: WishlistSerializer},
    ),
)
class WishlistListView(APIView):
    """GET /api/v1/wishlist/ — список желаний пользователя."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        wishlist = WishlistService.get_or_create(request.user)
        serializer = WishlistSerializer(wishlist)
        return Response(serializer.data)


@extend_schema_view(
    post=extend_schema(
        summary='Добавить товар в избранное',
        request=AddToWishlistInputSerializer,
        responses={201: WishlistItemSerializer},
    ),
)
class WishlistAddView(APIView):
    """POST /api/v1/wishlist/add/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        input_ser = AddToWishlistInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        try:
            variant = ProductVariant.objects.get(pk=data['variant_id'])
        except ProductVariant.DoesNotExist:
            raise NotFound('Вариант товара не найден.')

        item = WishlistService.add_item(
            user=request.user,
            variant=variant,
            note=data.get('note', ''),
        )

        serializer = WishlistItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    delete=extend_schema(
        summary='Удалить товар из избранного',
        responses={204: 'Removed'},
    ),
)
class WishlistRemoveView(APIView):
    """DELETE /api/v1/wishlist/remove/{id}/"""
    permission_classes = (IsAuthenticated,)

    def delete(self, request, item_id):
        WishlistService.remove_item(request.user, item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(
        summary='Перенести в корзину',
        request=MoveToCartInputSerializer,
        responses={200: 'Moved'},
    ),
)
class WishlistMoveToCartView(APIView):
    """POST /api/v1/wishlist/move-to-cart/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        input_ser = MoveToCartInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        moved = WishlistService.move_to_cart(
            user=request.user,
            item_ids=data.get('item_ids'),
            variant_id=data.get('variant_id'),
            quantity=data.get('quantity', 1),
        )

        return Response({'moved': moved})


@extend_schema_view(
    post=extend_schema(
        summary='Очистить список желаний',
        responses={200: 'Cleared'},
    ),
)
class WishlistClearView(APIView):
    """POST /api/v1/wishlist/clear/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        count = WishlistService.clear(request.user)
        return Response({'removed': count})
