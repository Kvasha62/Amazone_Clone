from rest_framework import serializers

from .models import (
    Order,
    OrderItem
)


# 📦 Order Item
class OrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source='variant.product.name'
    )

    sku = serializers.CharField(
        source='variant.sku'
    )

    class Meta:
        model = OrderItem

        fields = [
            'id',
            'product_name',
            'sku',
            'price',
            'quantity',
            'total_price'
        ]


# 📦 Order
class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order

        fields = [
            'id',
            'status',
            'total_price',
            'shipping_address',
            'created_at',
            'items'
        ]
