from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers


User = get_user_model()


# 🔥 Регистрация
class RegisterSerializer(serializers.ModelSerializer):

    # Пароль
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User

        fields = [
            'id',
            'username',
            'email',
            'password'
        ]

    # Создание пользователя
    def create(self, validated_data):

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        return user


# 👤 Текущий пользователь
class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            'id',
            'username',
            'email'
        ]
