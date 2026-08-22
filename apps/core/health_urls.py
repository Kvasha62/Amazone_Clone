# ────────────────────────────────────────────────────────────────────────
# apps/core/health_urls.py — health-check для React.
#
# GET /api/v1/health/ → {"status": "ok", "version": "1.0.0"}
#
# React при запуске проверяет «живой ли бэкенд?».
# Без этого фронтенд-разработчик не понимает:
#   • Бэкенд не запущен?
#   • Сеть недоступна?
#   • Ошибка в API?
# ────────────────────────────────────────────────────────────────────────

from django.http import JsonResponse
from django.urls import path
from django.views import View


class HealthCheckView(View):
    """
    Health-check endpoint.

    GET /api/v1/health/

    Возвращает:
      {
          "status": "ok",
          "version": "1.0.0",
          "database": "ok"
      }

    Используется React-приложением для проверки доступности бэкенда.
    """

    def get(self, request):
        # Проверяем что БД отвечает
        db_ok = True
        try:
            from django.db import connection
            connection.ensure_connection()
        except Exception:
            db_ok = False

        status_code = 200 if db_ok else 503

        return JsonResponse(
            {
                "status": "ok" if db_ok else "degraded",
                "version": "1.0.0",
                "database": "ok" if db_ok else "error",
            },
            status=status_code,
        )


urlpatterns = [
    path('', HealthCheckView.as_view(), name='health'),
]
