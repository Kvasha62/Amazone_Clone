from decimal import Decimal

from rest_framework import serializers

from apps.cart.constants import MAX_ITEM_QUANTITY
from apps.cart.models import Cart, CartItem


# ==========================================================
# INPUT-СЕРИАЛИЗАТОРЫ (валидация запросов)
# ==========================================================

class AddToCartInputSerializer(serializers.Serializer):
    """Валидация тела POST /cart/items."""

    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=MAX_ITEM_QUANTITY,
        default=1,
    )


class UpdateCartItemInputSerializer(serializers.Serializer):
    """Валидация тела PATCH /cart/items/<id>."""

    quantity = serializers.IntegerField(
        min_value=1,
        max_value=MAX_ITEM_QUANTITY,
    )


# ==========================================================
# OUTPUT-СЕРИАЛИЗАТОРЫ (ответы API)
# ==========================================================

class CartItemSerializer(serializers.ModelSerializer):
    """Позиция корзины — только чтение."""

    product_name = serializers.CharField(
        source='variant.product.name',
        read_only=True,
    )
    sku = serializers.CharField(
        source='variant.sku',
        read_only=True,
    )

    # price / total_price — DecimalField с allow_null,
    # т.к. unit_price может быть None (нет цены у варианта).
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        source='unit_price',
        allow_null=True,
        read_only=True,
    )
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        source='total_price',
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = (
            'id',
            'product_name',
            'sku',
            'price',
            'quantity',
            'total_price',
        )
        read_only_fields = fields


class CartSerializer(serializers.ModelSerializer):
    """Корзина целиком."""

    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            'id',
            'items',
            'total',
            'total_quantity',
        )
        read_only_fields = fields

    def get_total(self, obj: Cart) -> Decimal:
        """
        Общая стоимость корзины.
        Стартуем с Decimal('0.00'), чтобы при пустой корзине
        вернуть Decimal, а не int 0.
        """
        return sum(
            (item.total_price or Decimal('0.00') for item in obj.items.all()),
            Decimal('0.00'),
        )

    def get_total_quantity(self, obj: Cart) -> int:
        return sum(item.quantity for item in obj.items.all())
