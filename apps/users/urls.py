# ────────────────────────────────────────────────────────────────────────
# apps/users/urls.py — URL-маршруты модуля пользователей.
#
# Подключается в config/urls.py:
#   path('api/v1/', include('apps.users.urls'))
#
# ДВЕ ГРУППЫ ЭНДПОИНТОВ:
#   /api/v1/auth/*    — аутентификация (JWT + регистрация + смена пароля)
#   /api/v1/users/*   — профиль и адреса (требуют JWT)
#
# SimpleJWT предоставляет TokenObtainPairView (login) и
# TokenRefreshView (refresh) — встроенные view без нашей логики.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/http/urls/
# 📖 https://django-rest-framework-simplejwt.readthedocs.io/en/latest/getting_started.html
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

# SimpleJWT — стандартные view для JWT-авторизации.
# 🔴 EmailTokenObtainPairView — кастомный login по email (не username)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from apps.users.api_views.auth_views import RegisterView, ChangePasswordView
from apps.users.api_views.user_views import MeView
from apps.users.api_views.address_views import (
    AddressListView,
    AddressDetailView,
    AddressDefaultView,
)
from apps.users.api_views.jwt_email_views import EmailTokenObtainPairView

# app_name — namespace для reverse(): reverse('users:me')
app_name = 'users'

urlpatterns = [
    # ==========================================================
    # Auth (публичные — AllowAny)
    # ==========================================================
    path('auth/register/', RegisterView.as_view(), name='register'),
    # 🔴 JWT login по EMAIL (не username)
    # POST {"email": "...", "password": "..."} → {"access": "...", "refresh": "..."}
    path('auth/login/', EmailTokenObtainPairView.as_view(), name='login'),
    # SimpleJWT refresh: POST {refresh} → {access}
    path('auth/refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),

    # ==========================================================
    # Profile (авторизованные — IsAuthenticated)
    # ==========================================================
    path('users/me/', MeView.as_view(), name='me'),

    # ==========================================================
    # Addresses (авторизованные — IsAuthenticated)
    # ==========================================================
    path('users/addresses/', AddressListView.as_view(), name='address-list'),
    # <int:address_id> — конвертер: только целые числа
    path('users/addresses/<int:address_id>/', AddressDetailView.as_view(), name='address-detail'),
    # /default/ — статический маршрут ДО динамического (хотя <int:...> не совпадёт)
    path('users/addresses/<int:address_id>/default/', AddressDefaultView.as_view(), name='address-default'),
]
