# ────────────────────────────────────────────────────────────────────────
# apps/users/api_views/auth_views.py — регистрация и смена пароля.
#
# ЭНДПОИНТЫ:
#   POST /api/v1/auth/register/          — RegisterView
#   POST /api/v1/auth/change-password/   — ChangePasswordView
#
# PROD-002: бизнес-мутации User идут только через UserService
# (register / change_password). View — HTTP + валидация.
#
# 📖 https://www.django-rest-framework.org/api-guide/views/
# ────────────────────────────────────────────────────────────────────────

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.users.services.user_service import UserService

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


# ================================================================
# Сериализаторы (inline — используются только здесь)
# ================================================================

class RegisterInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name = serializers.CharField(max_length=150, required=False, default='')

    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError(
                {'password_confirm': 'Пароли не совпадают.'},
            )
        return data


class RegisterOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class ChangePasswordInputSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data.get('new_password') != data.get('new_password_confirm'):
            raise serializers.ValidationError(
                {'new_password_confirm': 'Пароли не совпадают.'},
            )
        return data


# ================================================================
# RegisterView
# ================================================================

@extend_schema_view(
    post=extend_schema(
        summary='Регистрация',
        request=RegisterInputSerializer,
        responses={201: RegisterOutputSerializer},
    ),
)
class RegisterView(APIView):
    """POST /api/v1/auth/register/ — регистрация нового пользователя."""
    permission_classes = (AllowAny,)

    def post(self, request):
        input_ser = RegisterInputSerializer(data=request.data)
        if not input_ser.is_valid():
            # 🔴 Логируем только ошибки валидации БЕЗ password/password_confirm
            safe_errors = {
                k: v for k, v in input_ser.errors.items()
                if k not in ('password', 'password_confirm')
            }
            logger.warning("Register validation error: %s", safe_errors)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        try:
            user = UserService.register(
                email=data['email'],
                username=data['username'],
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
            )
        except DRFValidationError as exc:
            # UserService raises field-keyed ValidationError → 400.
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        output = RegisterOutputSerializer(user)
        return Response(output.data, status=status.HTTP_201_CREATED)


# ================================================================
# ChangePasswordView
# ================================================================

@extend_schema_view(
    post=extend_schema(
        summary='Смена пароля',
        request=ChangePasswordInputSerializer,
        responses={200: 'Password changed'},
    ),
)
class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        input_ser = ChangePasswordInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        try:
            UserService.change_password(
                request.user,
                old_password=data['old_password'],
                new_password=data['new_password'],
            )
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Пароль успешно изменён.'})
