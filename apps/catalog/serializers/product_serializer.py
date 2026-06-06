from rest_framework import serializers

from apps.catalog.models.product import Product
from apps.catalog.models.product_variant import ProductVariant
from apps.catalog.models.product_image import ProductImage


# ==========================================================
# ИЗОБРАЖЕНИЕ ТОВАРА
# ==========================================================

class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage

        fields = (
            'id',
            'image',
            'is_main',
        )


# ==========================================================
# ВАРИАНТ ТОВАРА
# ==========================================================

class VariantSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductVariant

        fields = (
            'id',
            'sku',
            'slug',
        )


# ==========================================================
# ТОВАР
# ==========================================================

class ProductSerializer(serializers.ModelSerializer):

    brand_name = serializers.CharField(
        source='brand.name',
        read_only=True
    )

    category_name = serializers.CharField(
        source='category.full_name_cached',
        read_only=True
    )

    price = serializers.SerializerMethodField()

    variants = VariantSerializer(
        many=True,
        read_only=True
    )

    images = ProductImageSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Product

        fields = (
            'id',
            'name',
            'slug',
            'description',
            'brand_name',
            'category_name',
            'price',
            'is_active',
            'created_at',
            'updated_at',
            'variants',
            'images',
        )

    def get_price(self, obj):

        variants = list(obj.variants.all())

        if not variants:
            return None

        variant = variants[0]

        if not hasattr(variant, 'price'):
            return None

        return variant.price.price