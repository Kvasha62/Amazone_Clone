# ────────────────────────────────────────────────────────────────────────
# apps/users/api_views/address_views.py — API views для адресов доставки.
#
# ТРИ ЭНДПОИНТА:
#   AddressListView      — GET/POST  /api/v1/users/addresses/
#   AddressDetailView    — GET/PATCH/DELETE /api/v1/users/addresses/{id}/
#   AddressDefaultView   — POST /api/v1/users/addresses/{id}/default/
#
# Все требуют JWT-авторизацию (IsAuthenticated).
# IDOR protection: все методы проверяют что адрес принадлежит request.user.
#
# 📖 https://www.django-rest-framework.org/api-guide/views/
# 📖 https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
# ────────────────────────────────────────────────────────────────────────

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from apps.users.serializers import (
    AddressInputSerializer,
    AddressOutputSerializer,
)
from apps.users.services.address_service import AddressService

try:
    from drf_spectacular.utils import extend_schema, extend_schema_view
except ImportError:
    def extend_schema(**kwargs):
        def decorator(func): return func
        return decorator
    def extend_schema_view(**kwargs):
        def decorator(cls): return cls
        return decorator

logger = logging.getLogger(__name__)


class AddressThrottle(UserRateThrottle):
    """Throttle для адресов: 60/min."""
    rate = '60/min'


@extend_schema_view(
    get=extend_schema(summary='Список адресов', responses={200: AddressOutputSerializer(many=True)}),
    post=extend_schema(summary='Добавить адрес', request=AddressInputSerializer, responses={201: AddressOutputSerializer}),
)
class AddressListView(APIView):
    """
    GET  /api/v1/users/addresses/   — список адресов
    POST /api/v1/users/addresses/   — добавить адрес
    """
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AddressThrottle,)

    def get(self, request):
        """Список адресов: default первый, потом по дате."""
        addresses = AddressService.list_addresses(request.user)
        return Response(AddressOutputSerializer(addresses, many=True).data)

    def post(self, request):
        """Создание адреса с лимитом MAX_ADDRESSES_PER_USER."""
        serializer = AddressInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        address = AddressService.create_address(
            request.user,
            **serializer.validated_data,
        )
        return Response(
            AddressOutputSerializer(address).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(summary='Детали адреса'),
    patch=extend_schema(summary='Обновить адрес', request=AddressInputSerializer),
    delete=extend_schema(summary='Удалить адрес'),
)
class AddressDetailView(APIView):
    """
    GET    /api/v1/users/addresses/<id>/  — детали адреса
    PATCH  /api/v1/users/addresses/<id>/  — обновить
    DELETE /api/v1/users/addresses/<id>/  — удалить
    """
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AddressThrottle,)

    def get(self, request, address_id: int):
        """
        Получение адреса по ID.
        IDOR: filter(user=request.user) — чужой адрес → 404.
        """
        from apps.users.models import Address
        try:
            address = Address.objects.get(pk=address_id, user=request.user)
        except Address.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Адрес не найден.')
        return Response(AddressOutputSerializer(address).data)

    def patch(self, request, address_id: int):
        """
        Частичное обновление адреса.
        partial=True — позволяет передать подмножество полей.
        """
        serializer = AddressInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        address = AddressService.update_address(
            request.user,
            address_id,
            **serializer.validated_data,
        )
        return Response(AddressOutputSerializer(address).data)

    def delete(self, request, address_id: int):
        """Удаление адреса — 204 No Content."""
        AddressService.delete_address(request.user, address_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(summary='Установить адрес по умолчанию'),
)
class AddressDefaultView(APIView):
    """
    POST /api/v1/users/addresses/<id>/default/

    Устанавливает адрес как default (снимает с других).
    """
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AddressThrottle,)

    def post(self, request, address_id: int):
        address = AddressService.set_default(request.user, address_id)
        return Response(AddressOutputSerializer(address).data)
