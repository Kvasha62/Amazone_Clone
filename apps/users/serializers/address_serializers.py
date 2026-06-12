# ────────────────────────────────────────────────────────────────────────
# apps/users/serializers/address_serializers.py — сериализаторы адресов.
#
# AddressInputSerializer  — валидация POST/PATCH (input)
# AddressOutputSerializer — сериализация адреса (output, read-only)
#
# 📖 https://www.django-rest-framework.org/api-guide/serializers/
# ────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from apps.users.models import Address


class AddressInputSerializer(serializers.Serializer):
    """
    Валидация тела POST/PATCH для адресов.

    ПОЧЕМУ Serializer, А НЕ ModelSerializer:
        Адрес создаётся через AddressService.create_address(),
        а не напрямую через serializer.save(). Serializer только валидирует.
    """
    recipient_name = serializers.CharField(max_length=200)
    country = serializers.CharField(max_length=100, required=False, default='Россия')
    region = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    city = serializers.CharField(max_length=100)
    street = serializers.CharField(max_length=300)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    is_default = serializers.BooleanField(required=False, default=False)


class AddressOutputSerializer(serializers.ModelSerializer):
    """
    Адрес доставки — только чтение.
    Все поля read-only — создание/обновление через AddressService.
    """
    class Meta:
        model = Address
        fields = (
            'id', 'recipient_name', 'country', 'region', 'city',
            'street', 'postal_code', 'notes', 'is_default',
            'created_at', 'updated_at',
        )
        read_only_fields = fields
