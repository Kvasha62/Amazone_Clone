# ────────────────────────────────────────────────────────────────────────
# apps/analytics/apps.py — конфигурация модуля аналитики.
#
# Регистрирует приложение в Django и импортирует signals при ready().
# ────────────────────────────────────────────────────────────────────────

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analytics'
    verbose_name = 'Аналитика'

    def ready(self):
        import apps.analytics.signals  # noqa: F401
