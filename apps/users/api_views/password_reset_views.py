# ────────────────────────────────────────────────────────────────────────
# api_views/password_reset_views.py
# API-эндпоинты для восстановления пароля (token-based).
#
# ЭНДПОИНТЫ:
#   POST /api/v1/auth/password-reset/
#     Body: {"email": "user@example.com"}
#     → Отправляет email с токеном для сброса пароля.
#     → 200 OK (всегда — чтобы не утекала информация о существовании email)
#
#   POST /api/v1/auth/password-reset/confirm/
#     Body: {"uid": "...", "token": "...", "new_password": "..."}
#     → Устанавливает новый пароль.
#     → 200 OK или 400 Bad Request
#
# БЕЗОПАСНОСТЬ:
#   - Token генерируется Django (PasswordResetTokenGenerator)
#   - Token действует 3 дня (PASSWORD_RESET_TIMEOUT = 259200)
#   - Email не раскрывает существование аккаунта (всегда 200)
#   - UID — base64-кодировка PK пользователя
#
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/default/#resetting-passwords
# ────────────────────────────────────────────────────────────────────────

import logging

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User

try:
    from drf_spectacular.utils import extend_schema
except ImportError:
    def extend_schema(**kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)


# ── Serializers ─────────────────────────────────────────────

class PasswordResetRequestSerializer(serializers.Serializer):
    """Валидация запроса на сброс пароля."""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Валидация подтверждения сброса пароля."""
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, max_length=128)
    new_password_confirm = serializers.CharField(min_length=8, max_length=128)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {'new_password_confirm': 'Пароли не совпадают.'}
            )
        return attrs


# ── Views ───────────────────────────────────────────────────

@extend_schema(
    summary='Запросить сброс пароля',
    description='Отправляет email с токеном для сброса пароля. Всегда возвращает 200.',
    request=PasswordResetRequestSerializer,
)
class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/

    Отправляет email с токеном для сброса пароля.
    Всегда возвращает 200 OK — не раскрывает существование аккаунта.
    """

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Тихо — не раскрываем существование email
            return Response({'detail': 'Если email существует, письмо отправлено.'})

        if user.has_usable_password():
            # Генерируем uid и token
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # TODO: Отправить email через Celery task
            # send_password_reset_email.delay(user.pk, uid, token)
            logger.info(
                'Password reset requested for user %s (uid=%s, token=%s)',
                user.pk, uid, token,
            )

        # Всегда 200 — не утекает информация
        return Response({'detail': 'Если email существует, письмо отправлено.'})


@extend_schema(
    summary='Подтвердить сброс пароля',
    description='Устанавливает новый пароль по токену из email.',
    request=PasswordResetConfirmSerializer,
)
class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/

    Устанавливает новый пароль по uid + token из email.
    """

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        # Декодируем uid → user PK
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'detail': 'Недействительная ссылка для сброса пароля.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем токен
        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Недействительный или просроченный токен.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Устанавливаем новый пароль
        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'])

        logger.info('Password reset confirmed for user %s', user.pk)

        return Response({'detail': 'Пароль успешно изменён.'})
