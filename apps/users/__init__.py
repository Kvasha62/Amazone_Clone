# ────────────────────────────────────────────────────────────────────────
# apps/users/__init__.py — конфигурация приложения «Пользователи».
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/#configuring-applications
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • INSTALLED_APPS не найдёт apps.users → модели не загрузятся
#   • AUTH_USER_MODEL = 'users.User' → LookupError
# ────────────────────────────────────────────────────────────────────────

# AppConfig — конфигурация Django-приложения.
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Конфигурация приложения «Пользователи».

    default_auto_field = BigAutoField — 64-bit PK.
    name = 'apps.users' — путь к пакету.
    verbose_name = 'Пользователи' — заголовок в Admin.
    ready() — подключает сигнал create_user_profile.

    📖 https://docs.djangoproject.com/en/stable/ref/applications/
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Пользователи'

    def ready(self):
        """
        Импортирует signals.py → регистрирует @receiver(post_save, sender=User).
        📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.ready
        """
        import apps.users.signals  # noqa: F401
