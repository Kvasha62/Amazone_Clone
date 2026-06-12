# ────────────────────────────────────────────────────────────────────────
# apps/users/api_views/auth_views.py — регистрация и смена пароля.
#
# ЭНДПОИНТЫ:
#   POST /api/v1/auth/register/          — RegisterView
#   POST /api/v1/auth/change-password/   — ChangePasswordView
#
# 📖 https://www.django-rest-framework.org/api-guide/views/
# ────────────────────────────────────────────────────────────────────────

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from apps.users.models import User

try:
    from drf_spectacular.utils import extend_schema, extend_schema_view
except ImportError:
    def extend_schema(**kwargs):
        def decorator(func): return func
        return decorator
    def extend_schema_view(**kwargs):
        def decorator(cls): return cls
        return decorator


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
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        # Проверка уникальности email
        if User.objects.filter(email__iexact=data['email']).exists():
            return Response(
                {'email': 'Пользователь с таким email уже существует.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверка уникальности username
        if User.objects.filter(username=data['username']).exists():
            return Response(
                {'username': 'Пользователь с таким именем уже существует.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )

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

        user = request.user

        if not user.check_password(data['old_password']):
            return Response(
                {'old_password': 'Неверный текущий пароль.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(data['new_password'])
        user.save()

        return Response({'detail': 'Пароль успешно изменён.'})
