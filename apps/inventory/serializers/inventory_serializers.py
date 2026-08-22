# ────────────────────────────────────────────────────────────────────────
# apps/inventory/serializers/inventory_serializers.py — сериализаторы склада.
#
# ЧЕТЫРЕ СЕРИАЛИЗАТОРА:
#   1. RestockInputSerializer      — валидация POST body (пополнение)
#   2. AdjustStockInputSerializer  — валидация POST body (корректировка)
#   3. StockSerializer             — сериализация остатков (output)
#   4. StockMovementSerializer     — сериализация движения (output)
#
# 📖 https://www.django-rest-framework.org/api-guide/serializers/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Все API endpoints склада → ImportError (500)
# ────────────────────────────────────────────────────────────────────────

from rest_framework import serializers

from apps.inventory.models import Stock, StockMovement
from apps.inventory.models.stock_movement import MovementKind


# ==============================================================
# INPUT-СЕРИАЛИЗАТОРЫ
# ==============================================================

class RestockInputSerializer(serializers.Serializer):
    """
    Валидация тела POST /api/v1/inventory/{variant_id}/restock/.

    ФОРМАТ ЗАПРОСА:
        {"quantity": 100, "note": "Приёмка по накладной №12345"}
    """
    quantity = serializers.IntegerField(min_value=1, max_value=100000)
    note = serializers.CharField(max_length=500, required=False, default='', allow_blank=True)


class AdjustStockInputSerializer(serializers.Serializer):
    """
    Валидация тела POST /api/v1/inventory/{variant_id}/adjust/.

    ФОРМАТ ЗАПРОСА:
        {"new_quantity": 50, "note": "Инвентаризация: найдено 5 брака"}
    """
    new_quantity = serializers.IntegerField(min_value=0, max_value=100000)
    note = serializers.CharField(max_length=500, required=False, default='', allow_blank=True)


# ==============================================================
# OUTPUT-СЕРИАЛИЗАТОРЫ
# ==============================================================

class StockSerializer(serializers.ModelSerializer):
    """
    Остатки варианта на складе.

    ВЫВОДИТ:
        {
            "id": 1,
            "variant_id": 42,
            "sku": "IP15P-128-BLK",
            "product_name": "iPhone 15 Pro 128GB",
            "quantity": 100,
            "reserved_quantity": 30,
            "available_quantity": 70,
            "is_low_stock": false,
            "is_out_of_stock": false,
            "low_stock_threshold": 5
        }
    """
    variant_id = serializers.IntegerField(read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    product_name = serializers.CharField(
        source='variant.product.name', read_only=True,
    )
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Stock
        fields = (
            'id',
            'variant_id',
            'sku',
            'product_name',
            'quantity',
            'reserved_quantity',
            'available_quantity',
            'is_low_stock',
            'is_out_of_stock',
            'low_stock_threshold',
        )
        read_only_fields = fields


class StockMovementSerializer(serializers.ModelSerializer):
    """
    Запись о движении товара.

    ВЫВОДИТ:
        {
            "id": 1,
            "kind": "reserve",
            "kind_display": "Резервирование",
            "delta": 30,
            "quantity_before": 100,
            "quantity_after": 100,
            "note": "Резерв под заказ ORD-000123",
            "order_number": "ORD-000123",
            "performed_by_email": "admin@example.com",
            "created_at": "2026-06-12T14:30:00Z"
        }
    """
    kind_display = serializers.CharField(
        source='get_kind_display', read_only=True,
    )
    order_number = serializers.CharField(
        source='order.order_number', read_only=True, default=None,
    )
    performed_by_email = serializers.CharField(
        source='performed_by.email', read_only=True, default=None,
    )

    class Meta:
        model = StockMovement
        fields = (
            'id',
            'kind',
            'kind_display',
            'delta',
            'quantity_before',
            'quantity_after',
            'note',
            'order_number',
            'performed_by_email',
            'created_at',
        )
        read_only_fields = fields
