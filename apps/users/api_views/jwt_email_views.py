# ────────────────────────────────────────────────────────────────────────
# apps/users/api_views/jwt_email_views.py — кастомная JWT-авторизация по email.
#
# 🔴 ПРОБЛЕМА: SimpleJWT TokenObtainPairView по умолчанию
#   ожидает {username, password}. Наш User регистрируется по email.
#   React-форма логина отправляет {email, password} → 401.
#
# РЕШЕНИЕ: Кастомный сериализатор, который ищет пользователя по email
#   и генерирует токен напрямую, минуя родительский authenticate().
# ────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.models import User


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT-сериализатор, принимающий email вместо username.

    ЗАПРОС:
      POST /api/v1/auth/login/
      {
          "email": "ivan@example.com",
          "password": "secret123"
      }

    ОТВЕТ:
      {
          "access": "eyJ...",
          "refresh": "eyJ..."
      }

    АЛГОРИТМ:
      1. Валидируем email + password
      2. Ищем пользователя по email (case-insensitive)
      3. Проверяем пароль
      4. Генерируем JWT-токен через get_token()
    """

    username_field = 'email'

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username', None)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise AuthenticationFailed(
                'Необходимо указать email и пароль.',
            )

        # Ищем пользователя по email (case-insensitive)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                'Неверный email или пароль.',
            )

        # Проверяем пароль
        if not user.check_password(password):
            raise AuthenticationFailed(
                'Неверный email или пароль.',
            )

        if not user.is_active:
            raise AuthenticationFailed(
                'Аккаунт деактивирован.',
            )

        # Генерируем токен напрямую, минуя parent.validate()
        # (parent.validate() вызывает authenticate() который не понимает email)
        refresh = self.get_token(user)

        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return data

    @classmethod
    def get_token(cls, user):
        """Генерирует JWT-токен для пользователя."""
        return TokenObtainPairSerializer.get_token(user)


class EmailTokenObtainPairView(TokenObtainPairView):
    """
    JWT login по email.

    POST /api/v1/auth/login/
    Body: {"email": "...", "password": "..."}
    Response: {"access": "...", "refresh": "..."}
    """
    serializer_class = EmailTokenObtainPairSerializer
