# ────────────────────────────────────────────────────────────────────────
# apps/analytics/serializers/analytics_serializers.py
#
# Сериализаторы для аналитических данных.
# Большинство — SerializerMethodField / DictField, т.к. данные —
# агрегации, а не модели.
#
# 📖 https://www.django-rest-framework.org/api-guide/serializers/
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from rest_framework import serializers


# ================================================================
# Входные параметры
# ================================================================

class AnalyticsDateRangeSerializer(serializers.Serializer):
    """Параметры запроса: период анализа."""

    days = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        help_text='Количество дней для анализа (по умолчанию 30).',
    )


# ================================================================
# Выходные данные: сводка продаж
# ================================================================

class SalesSummarySerializer(serializers.Serializer):
    """Сводка продаж за период."""

    total_revenue = serializers.DecimalField(
        max_digits=14, decimal_places=2,
    )
    total_orders = serializers.IntegerField()
    confirmed_orders = serializers.IntegerField()
    delivered_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    processing_orders = serializers.IntegerField()
    shipped_orders = serializers.IntegerField()
    avg_order_value = serializers.DecimalField(
        max_digits=14, decimal_places=2,
    )
    total_items_sold = serializers.IntegerField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()


# ================================================================
# Выходные данные: временной ряд
# ================================================================

class SalesTimelineItemSerializer(serializers.Serializer):
    """Один элемент временного ряда."""

    date = serializers.CharField()
    orders_count = serializers.IntegerField()
    revenue = serializers.CharField()
    items_sold = serializers.IntegerField()


class SalesTimelineSerializer(serializers.Serializer):
    """Временной ряд продаж (для графиков)."""

    timeline = SalesTimelineItemSerializer(many=True)


# ================================================================
# Выходные данные: топы
# ================================================================

class TopProductSerializer(serializers.Serializer):
    """Топ-товар."""

    variant_id = serializers.IntegerField(allow_null=True)
    product_name = serializers.CharField()
    sku = serializers.CharField()
    quantity_sold = serializers.IntegerField()
    revenue = serializers.CharField()


class TopCategorySerializer(serializers.Serializer):
    """Топ-категория."""

    category_id = serializers.IntegerField(allow_null=True)
    category_name = serializers.CharField()
    orders_count = serializers.IntegerField()
    revenue = serializers.CharField()


class TopCustomerSerializer(serializers.Serializer):
    """Топ-покупатель."""

    user_id = serializers.IntegerField()
    email = serializers.CharField()
    orders_count = serializers.IntegerField()
    total_spent = serializers.CharField()


# ================================================================
# Выходные данные: просмотры и конверсия
# ================================================================

class ProductViewSerializer(serializers.Serializer):
    """Просмотр товара."""

    id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    product_name = serializers.CharField(
        source='product.name',
        read_only=True,
    )
    source = serializers.CharField()
    created_at = serializers.DateTimeField()


class ConversionRateSerializer(serializers.Serializer):
    """Конверсия."""

    total_views = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    conversion_rate = serializers.DecimalField(
        max_digits=6, decimal_places=2,
    )


# ================================================================
# Dashboard
# ================================================================

class DashboardResponseSerializer(serializers.Serializer):
    """Комплексный дашборд."""

    summary = SalesSummarySerializer()
    top_products = TopProductSerializer(many=True)
    top_categories = TopCategorySerializer(many=True)
    top_customers = TopCustomerSerializer(many=True)
    conversion = ConversionRateSerializer()
    timeline = SalesTimelineItemSerializer(many=True)
