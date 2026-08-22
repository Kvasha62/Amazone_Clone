# ────────────────────────────────────────────────────────────────────────
# apps/pricing/serializers/price_serializers.py — сериализаторы цен.
#
# INPUT:  SetPriceInputSerializer, BulkPriceItemSerializer, BulkSetPricesInputSerializer
# OUTPUT: PriceSerializer, PriceHistorySerializer
#
# 📖 https://www.django-rest-framework.org/api-guide/serializers/
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from rest_framework import serializers

from apps.pricing.models import Price, PriceHistory


# ==========================================================
# INPUT
# ==========================================================

class SetPriceInputSerializer(serializers.Serializer):
    """
    Валидация POST /pricing/variants/<id>/price/.
    variant_id НЕ нужен — приходит из URL path.
    """
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
    )
    sale_price = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True, default=None,
    )
    reason = serializers.CharField(
        max_length=255, required=False, default='', allow_blank=True,
    )


class BulkPriceItemSerializer(serializers.Serializer):
    """
    Один элемент в массиве массового обновления.
    В отличие от SetPriceInputSerializer — содержит variant_id.
    """
    variant_id = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
    )
    sale_price = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True, default=None,
    )


class BulkSetPricesInputSerializer(serializers.Serializer):
    """
    Валидация POST /pricing/prices/bulk/.
    { "prices": [ {...}, {...} ] }
    """
    # BulkPriceItemSerializer(many=True) — валидирует массив объектов.
    prices = BulkPriceItemSerializer(many=True)


# ==========================================================
# OUTPUT
# ==========================================================

class PriceSerializer(serializers.ModelSerializer):
    """
    Цена варианта — чтение.
    effective_price и discount_percent — computed properties.
    """
    effective_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    discount_percent = serializers.IntegerField(
        read_only=True, allow_null=True,
    )

    class Meta:
        model = Price
        fields = (
            'id', 'variant', 'price', 'sale_price', 'currency',
            'effective_price', 'discount_percent',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


class PriceHistorySerializer(serializers.ModelSerializer):
    """История изменения цены — чтение."""
    class Meta:
        model = PriceHistory
        fields = (
            'id', 'old_price', 'new_price',
            'old_sale_price', 'new_sale_price',
            'changed_by', 'reason', 'created_at',
        )
        read_only_fields = fields
