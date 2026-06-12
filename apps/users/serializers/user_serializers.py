# ────────────────────────────────────────────────────────────────────────
# apps/users/serializers/user_serializers.py — сериализаторы пользователей.
#
# INPUT: RegisterInputSerializer, ChangePasswordInputSerializer, UpdateProfileInputSerializer
# OUTPUT: UserProfileSerializer, UserDetailSerializer, UserShortSerializer
#
# 📖 https://www.django-rest-framework.org/api-guide/serializers/
# 📖 https://www.django-rest-framework.org/api-guide/fields/
# ────────────────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import UserProfile, Address
from apps.users.constants import MIN_PASSWORD_LENGTH

User = get_user_model()


# ==========================================================
# INPUT-СЕРИАЛИЗАТОРЫ
# ==========================================================

class RegisterInputSerializer(serializers.Serializer):
    """
    Валидация POST /auth/register/.

    password_confirm — поле подтверждения пароля.
    write_only=True — НЕ включается в ответ (пароль не утекает).

    📖 https://www.django-rest-framework.org/api-guide/fields/#charfield
    """
    email = serializers.EmailField(max_length=254)       # RFC 5321 limit
    username = serializers.CharField(min_length=3, max_length=150)
    password = serializers.CharField(
        min_length=MIN_PASSWORD_LENGTH, max_length=128, write_only=True,
    )
    password_confirm = serializers.CharField(
        min_length=MIN_PASSWORD_LENGTH, max_length=128, write_only=True,
    )
    first_name = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, default='', allow_blank=True)

    def validate(self, data):
        """
        Объектная валидация — проверка совпадения паролей.

        Вызывается ПОСЛЕ field-level валидации.
        data — словарь валидных значений полей.
        📖 https://www.django-rest-framework.org/api-guide/serializers/#object-level-validation
        """
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают.',
            })
        return data

    def validate_username(self, value):
        """
        Field-level валидация — формат username.

        Regex: ^[``\\w``.@+-]+$ — стандартный Django pattern для username.
        Буквы (Unicode), цифры, @, ., +, -, _.
        📖 https://docs.djangoproject.com/en/stable/ref/contrib/auth/#django.contrib.auth.models.User.username
        """
        import re
        if not re.match(r'^[a-zA-Z0-9_.@+-]+$', value):
            raise serializers.ValidationError(
                'Имя пользователя может содержать только буквы, '
                'цифры и символы @/./+/-/_.'
            )
        return value


class ChangePasswordInputSerializer(serializers.Serializer):
    """Валидация POST /auth/change-password/."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        min_length=MIN_PASSWORD_LENGTH, max_length=128, write_only=True,
    )
    new_password_confirm = serializers.CharField(
        min_length=MIN_PASSWORD_LENGTH, max_length=128, write_only=True,
    )

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Пароли не совпадают.',
            })
        return data


class UpdateProfileInputSerializer(serializers.Serializer):
    """
    Валидация PATCH /users/me/.
    Все поля optional (required=False) — PATCH semantics.
    """
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=UserProfile.GenderChoices.choices, required=False, allow_blank=True,
    )
    timezone = serializers.CharField(max_length=50, required=False)
    language = serializers.CharField(max_length=10, required=False)
    email_subscribed = serializers.BooleanField(required=False)


# ==========================================================
# OUTPUT-СЕРИАЛИЗАТОРЫ
# ==========================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор профиля (вложенный в UserDetail).
    Все поля read-only — профиль обновляется через UpdateProfileInputSerializer.
    """
    class Meta:
        model = UserProfile
        fields = ('avatar', 'date_of_birth', 'gender', 'timezone', 'language', 'email_subscribed')
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Полная информация о пользователе (profile вложен).
    GET /users/me/ → { id, email, username, ..., profile: {...} }
    """
    profile = UserProfileSerializer(read_only=True)  # Вложенный сериализатор
    full_name = serializers.CharField(read_only=True)  # Property модели User

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'phone', 'is_active', 'date_joined', 'profile',
        )
        read_only_fields = fields


class UserShortSerializer(serializers.ModelSerializer):
    """
    Краткая информация (для отзывов, заказов — где не нужен полный профиль).
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name')
        read_only_fields = fields
