import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.cart.serializers import (
    AddToCartInputSerializer,
    CartSerializer,
    UpdateCartItemInputSerializer,
)
from apps.cart.services.cart_service import CartService

# drf-spectacular — опциональная зависимость.
# Если пакет не установлен, декораторы становятся no-op.
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


# ==========================================================
# ОБЩАЯ ЛОГИКА
# ==========================================================

class _CartViewMixin:
    """
    Общая логика для всех cart-view:
      - получаем / создаём корзину
      - перечитываем с prefetch'ами для сериализации
    """

    permission_classes = (AllowAny,)

    def _get_cart(self, request) -> Cart:
        return CartService.get_or_create_cart(request)

    def _reload_cart(self, cart: Cart) -> Cart:
        """
        Перечитывает корзину с prefetch для сериализации.

        Используем with_items() без active() — мы уже знаем PK корзины,
        фильтр по is_active здесь не нужен (и ломал бы сериализацию
        после merge, где гостевая корзина деактивирована).
        """
        return Cart.objects.with_items().get(pk=cart.pk)

    def _serialize_cart(self, cart: Cart) -> dict:
        return CartSerializer(cart).data

    def _respond_cart(
        self,
        cart: Cart,
        *,
        reload: bool = True,
        status_code: int = status.HTTP_200_OK,
    ) -> Response:
        """
        Утилита: перезагружает (опционально) и возвращает Response.
        Параметр reload=False используется, когда данные уже свежие.
        """
        if reload:
            cart = self._reload_cart(cart)
        return Response(self._serialize_cart(cart), status=status_code)


# ==========================================================
# /api/cart/
# ==========================================================

@extend_schema_view(
    get=extend_schema(
        summary='Получить корзину',
        description='Возвращает текущую корзину пользователя или гостя.',
    ),
    delete=extend_schema(
        summary='Очистить корзину',
        description='Удаляет все позиции из корзины.',
    ),
)
class CartView(_CartViewMixin, APIView):
    """
    GET    /api/cart/   — получить корзину
    DELETE /api/cart/   — очистить корзину
    """

    def get(self, request):
        cart = self._get_cart(request)
        return self._respond_cart(cart)

    def delete(self, request):
        cart = self._get_cart(request)
        CartService.clear(cart)
        return self._respond_cart(cart)


# ==========================================================
# /api/cart/items/
# ==========================================================

@extend_schema_view(
    post=extend_schema(
        summary='Добавить товар в корзину',
        description='Добавляет вариант товара или увеличивает количество.',
        request=AddToCartInputSerializer,
    ),
)
class CartItemView(_CartViewMixin, APIView):
    """
    POST /api/cart/items/   — добавить вариант в корзину
        body: {"variant_id": 1, "quantity": 2}
    """

    def post(self, request):
        input_serializer = AddToCartInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        cart = self._get_cart(request)
        CartService.add_item(
            cart=cart,
            variant_id=input_serializer.validated_data['variant_id'],
            quantity=input_serializer.validated_data['quantity'],
        )
        return self._respond_cart(
            cart,
            status_code=status.HTTP_201_CREATED,
        )


# ==========================================================
# /api/cart/items/<id>/
# ==========================================================

@extend_schema_view(
    patch=extend_schema(
        summary='Изменить количество',
        description='Обновляет количество единиц позиции.',
        request=UpdateCartItemInputSerializer,
    ),
    delete=extend_schema(
        summary='Удалить позицию',
        description='Удаляет позицию из корзины.',
    ),
)
class CartItemDetailView(_CartViewMixin, APIView):
    """
    PATCH  /api/cart/items/<id>/  — изменить количество
        body: {"quantity": 5}
    DELETE /api/cart/items/<id>/  — удалить позицию
    """

    def patch(self, request, item_id: int):
        input_serializer = UpdateCartItemInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        cart = self._get_cart(request)
        CartService.update_item_quantity(
            cart=cart,
            item_id=item_id,
            quantity=input_serializer.validated_data['quantity'],
        )
        return self._respond_cart(cart)

    def delete(self, request, item_id: int):
        cart = self._get_cart(request)
        CartService.remove_item(cart=cart, item_id=item_id)
        return self._respond_cart(cart)


# ==========================================================
# /api/cart/merge/  — явное слияние для JWT / Token auth
# ==========================================================

@extend_schema_view(
    post=extend_schema(
        summary='Слить гостевую корзину',
        description=(
            'Переносит позиции из гостевой корзины в корзину '
            'текущего пользователя. Вызывать после получения JWT-токена. '
            'Session-key берётся из текущей сессии.'
        ),
    ),
)
class CartMergeView(APIView):
    """
    POST /api/cart/merge/

    Явное слияние гостевой корзины в пользовательскую.
    Необходим при JWT / Token-авторизации, т.к. сигнал
    user_logged_in не срабатывает для stateless-методов.

    Требует авторизацию (IsAuthenticated).
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        session_key = request.session.session_key
        if not session_key:
            return Response(
                {'detail': 'Сессия гостя не найдена.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_cart = CartService.merge_guest_into_user_cart(
            session_key, request.user,
        )
        if user_cart is None:
            return Response(
                {'detail': 'Гостевая корзина не найдена.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Сериализуем итоговую корзину
        cart = Cart.objects.with_items().get(pk=user_cart.pk)
        return Response(CartSerializer(cart).data)
