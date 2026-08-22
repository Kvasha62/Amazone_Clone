# ────────────────────────────────────────────────────────────────────────
# apps/users/api_views/user_views.py — API views для профиля пользователя.
#
# ЭНДПОИНТ /api/v1/users/me/:
#   GET    — данные текущего пользователя (с профилем)
#   PATCH  — обновить профиль
#   DELETE — деактивировать аккаунт
#
# Все методы требуют JWT-авторизацию (IsAuthenticated).
#
# 📖 https://www.django-rest-framework.org/api-guide/views/
# 📖 https://www.django-rest-framework.org/api-guide/permissions/#isauthenticated
# ────────────────────────────────────────────────────────────────────────

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from apps.users.models import User
from apps.users.serializers import (
    UpdateProfileInputSerializer,
    UserDetailSerializer,
)
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


class ProfileUserThrottle(UserRateThrottle):
    """Throttle для профиля: 60/min."""
    rate = '60/min'


@extend_schema_view(
    get=extend_schema(summary='Мой профиль', description='Данные текущего пользователя с профилем.'),
    patch=extend_schema(summary='Обновить профиль', request=UpdateProfileInputSerializer),
    delete=extend_schema(summary='Деактивировать аккаунт'),
)
class MeView(APIView):
    """
    GET    /api/v1/users/me/   — данные текущего пользователя
    PATCH  /api/v1/users/me/   — обновить профиль
    DELETE /api/v1/users/me/   — деактивировать аккаунт (is_active=False)
    """
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ProfileUserThrottle,)

    def get(self, request):
        """
        GET /users/me/

        with_profile() — select_related('profile') → JOIN в 1 запрос.
        Без: user.profile → 2-й SQL.
        """
        user = User.objects.with_profile().get(pk=request.user.pk)
        return Response(UserDetailSerializer(user).data)

    def patch(self, request):
        """
        PATCH /users/me/ — частичное обновление.

        Валидация → UserService.update_profile() → перечитывание → ответ.
        """
        serializer = UpdateProfileInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = UserService.update_profile(
            request.user,
            **serializer.validated_data,
        )

        # Перезагружаем с профилем для актуальных данных.
        user = User.objects.with_profile().get(pk=user.pk)
        return Response(UserDetailSerializer(user).data)

    def delete(self, request):
        """
        DELETE /users/me/ — мягкое удаление.

        Не удаляет из БД! Только is_active=False.
        Пользователь не сможет логиниться.
        """
        UserService.deactivate(request.user)
        return Response({'detail': 'Аккаунт деактивирован.'})
