from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор платежа.

    Преобразует объект Payment в JSON
    для React-приложения.
    """

    # Показываем ID заказа
    order_id = serializers.IntegerField(
        source='order.id',
        read_only=True
    )

    class Meta:
        model = Payment

        fields = (
            'id',
            'order_id',
            'amount',
            'currency',
            'status',
            'provider_payment_id',
            'created_at',
            'updated_at',
        )

        read_only_fields = (
            'id',
            'status',
            'provider_payment_id',
            'created_at',
            'updated_at',
        )