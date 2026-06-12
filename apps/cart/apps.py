# ────────────────────────────────────────────────────────────────────────
# apps/cart/apps.py — конфигурация Django-приложения «Корзина».
#
# AppConfig — класс, который Django использует для инициализации приложения.
# Выполняется ОДИН раз при старте Django (runserver / gunicorn / celery).
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.ready
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • default_app_config в __init__.py не найдёт класс → ImportError
#   • Сигнал user_logged_in не подключится → гостевые корзины не сольются
# ────────────────────────────────────────────────────────────────────────

# AppConfig — базовый класс Django для конфигурации приложения.
# Предоставляет: name, label, verbose_name, ready(), get_models(), ...
from django.apps import AppConfig


class CartConfig(AppConfig):
    """
    Конфигурация приложения «Корзина».

    Атрибуты AppConfig:
      • name — полное Python-имя пакета ('apps.cart').
        Django использует его для поиска модулей (models.py, urls.py, ...).
        📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.name

      • default_auto_field — тип первичного ключа для новых моделей.
        BigAutoField → BIGINT (64-bit) AUTO_INCREMENT.
        Без: Django создаст AutoField (32-bit) → при 2.1 млрд записей — переполнение.
        📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.BigAutoField

      • verbose_name — человекочитаемое имя для Django Admin.
        Отображается в заголовке раздела /admin/cart/.

      • ready() — метод, вызываемый после загрузки ВСЕХ приложений.
        Используется для подключения сигналов, регистрация checks и т.д.
    """

    # name — должен точно совпадать с путём к пакету в INSTALLED_APPS.
    # Если указать 'cart' вместо 'apps.cart' → Django не найдёт модели.
    name = 'apps.cart'

    # BigAutoField — BIGINT PK (поддержка >2 млрд записей).
    # В настройках проекта может быть указан другой default,
    # но здесь мы явно переопределяем для этого приложения.
    default_auto_field = 'django.db.models.BigAutoField'

    # Отображается в Admin: «Корзина» вместо «Cart».
    verbose_name = 'Корзина'

    def ready(self):
        """
        Вызывается после загрузки всех приложений Django.

        НАЗНАЧЕНИЕ:
          Подключает сигнал merge_guest_cart_on_login.

        КАК РАБОТАЕТ:
          import apps.cart.signals — при импорте модуля signals.py
          Python выполняет @receiver(user_logged_in) — декоратор
          регистрирует функцию merge_guest_cart_on_login
          в списке обработчиков сигнала user_logged_in.

        ПОЧЕМУ В ready(), А НЕ НА ВЕРХНЕМ УРОВНЕ МОДУЛЯ:
          Если импортировать signals на верхнем уровне apps.py →
          модели могут быть ещё не загружены → ImportError.
          ready() гарантирует, что ВСЕ модели уже доступны.

        ВНИМАНИЕ: user_logged_in срабатывает ТОЛЬКО при
        session-based авторизации (django.contrib.auth.login).
        При JWT-авторизации этот сигнал НЕ вызывается!
        Для JWT используйте POST /api/v1/cart/merge/ (CartMergeView).

        📖 https://docs.djangoproject.com/en/stable/ref/signals/#django.contrib.auth.signals.user_logged_in
        📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.ready
        """
        # import с побочным эффектом: при импорте модуля signals.py
        # выполняется @receiver(user_logged_in) — регистрация обработчика.
        # noqa: F401 — подавляем предупреждение «unused import» в линтерах.
        import apps.cart.signals  # noqa: F401
