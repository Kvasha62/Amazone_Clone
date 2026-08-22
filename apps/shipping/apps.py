# ────────────────────────────────────────────────────────────────────────
# apps/shipping/apps.py — конфигурация модуля доставки.
#
# Регистрирует приложение в Django и импортирует signals при ready().
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
# ────────────────────────────────────────────────────────────────────────

from django.apps import AppConfig


class ShippingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.shipping'
    verbose_name = 'Доставка и отправления'

    def ready(self):
        import apps.shipping.signals  # noqa: F401
