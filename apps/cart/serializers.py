from rest_framework import serializers

from .models import Cart, CartItem


# 📦 Cart Item
class CartItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source='variant.product.name'
    )

    sku = serializers.CharField(
        source='variant.sku'
    )

    price = serializers.DecimalField(
        source='variant.price.price',
        max_digits=10,
        decimal_places=2
    )

    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem

        fields = [
            'id',
            'product_name',
            'sku',
            'price',
            'quantity',
            'total_price'
        ]

    def get_total_price(self, obj):
        return obj.total_price


# 🛒 Cart
class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True)

    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart

        fields = [
            'id',
            'items',
            'total'
        ]

    # 💰 Общая сумма корзины
    def get_total(self, obj):
        return sum(item.total_price for item in obj.items.all())