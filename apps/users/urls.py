from django.urls import path

from rest_framework_simplejwt.views import (

    TokenObtainPairView,
    TokenRefreshView,
)

from .api_views import (
    RegisterAPIView,
    MeAPIView
)


urlpatterns = [

    # 🔥 Регистрация
    path(
        'api/auth/register/',
        RegisterAPIView.as_view()
    ),

    # 🔥 Login
    path(
        'api/auth/login/',
        TokenObtainPairView.as_view()
    ),

    # 🔥 Refresh
    path(
        'api/auth/refresh/',
        TokenRefreshView.as_view()
    ),

    # 🔥 Current user
    path(
        'api/auth/me/',
        MeAPIView.as_view()
    ),
]
