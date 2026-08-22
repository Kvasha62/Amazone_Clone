from decimal import Decimal

from rest_framework import serializers

from apps.wishlist.models import Wishlist, WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции в списке желаний."""

    product_name = serializers.CharField(
        source='variant.product.name',
        read_only=True,
    )
    sku = serializers.CharField(
        source='variant.sku',
        read_only=True,
    )
    effective_price = serializers.SerializerMethodField()
    variant_name = serializers.CharField(
        source='variant.name',
        read_only=True,
        default='',
    )
    is_available = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = (
            'id', 'variant_id', 'product_name', 'variant_name',
            'sku', 'effective_price', 'is_available',
            'image_url', 'note', 'sort_order', 'created_at',
        )
        read_only_fields = fields

    def get_effective_price(self, obj):
        price_obj = getattr(obj.variant, 'price', None)
        if price_obj:
            return str(price_obj.effective_price)
        return None

    def get_is_available(self, obj):
        return obj.variant.is_active and obj.variant.product.status == 'active'

    def get_image_url(self, obj):
        first_image = (
            obj.variant.product.images
            .order_by('order')
            .first()
        )
        if first_image:
            return first_image.image.url if first_image.image else None
        return None


class WishlistSerializer(serializers.ModelSerializer):
    """Сериализатор списка желаний."""

    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ('id', 'items_count', 'items', 'created_at', 'updated_at')
        read_only_fields = fields


class AddToWishlistInputSerializer(serializers.Serializer):
    """Запрос добавления товара в избранное."""

    variant_id = serializers.IntegerField(
        help_text='ID варианта товара.',
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )


class MoveToCartInputSerializer(serializers.Serializer):
    """Запрос переноса товаров из избранного в корзину."""

    item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='Список ID позиций для переноса.',
    )
    variant_id = serializers.IntegerField(
        required=False,
        help_text='ID варианта (единичный перенос).',
    )
    quantity = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text='Количество для корзины.',
    )
