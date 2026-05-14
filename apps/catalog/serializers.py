from rest_framework import serializers

from .models import (
    Product,
    ProductVariant,
    ProductImage
)


# 🖼 Serializer изображения
class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage

        fields = [
            'id',
            'image',
            'is_main'
        ]


# 📦 Serializer варианта
class VariantSerializer(serializers.ModelSerializer):

    # Цена
    price = serializers.DecimalField(
        source='price.price',
        max_digits=10,
        decimal_places=2
    )

    # Старая цена
    old_price = serializers.DecimalField(
        source='price.old_price',
        max_digits=10,
        decimal_places=2,
        allow_null=True
    )

    # Валюта
    currency = serializers.CharField(
        source='price.currency'
    )

    # Остаток
    stock = serializers.IntegerField(
        source='stock.quantity'
    )

    class Meta:
        model = ProductVariant

        fields = [
            'id',
            'sku',
            'slug',
            'price',
            'old_price',
            'currency',
            'stock'
        ]


# 🧠 Главный serializer товара
class ProductSerializer(serializers.ModelSerializer):

    # Варианты
    variants = VariantSerializer(many=True)

    # Изображения
    images = ProductImageSerializer(many=True)

    class Meta:
        model = Product

        fields = [
            'id',
            'name',
            'slug',
            'description',
            'brand',
            'variants',
            'images'
        ]