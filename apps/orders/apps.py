# ==============================================================================
# apps/orders/apps.py — Конфигурация приложения «orders» (Заказы)
# ==============================================================================
# Django-приложение — это Python-пакет с предопределённой структурой.
# AppConfig описывает метаданные приложения: имя, человекочитаемое
# название и тип первичного ключа.
#
# Этот файл загружается при старте Django (manage.py runserver,
# gunicorn, pytest) — ДО того, как модели готовы к использованию.
# Поэтому здесь нельзя импортировать модели.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Django не сможет загрузить приложение apps.orders
#   • INSTALLED_APPS упадёт с ImportError
# ==============================================================================

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """
    Конфигурация приложения apps.orders.

    Django создаёт экземпляр этого класса при загрузке и использует
    его для:
      - определения имени пакета (name)
      - типа первичного ключа по умолчанию (default_auto_field)
      - человекочитаемого названия в админке (verbose_name)
      - выполнения кода при старте (ready()) — здесь подключаем signals
    """

    # BigAutoField → BIGINT (64-битный) автоинкремент.
    # Заказов может быть миллионы — 32-битного int (~2.1 млрд) хватит
    # надолго, но BIGINT — стандарт для production.
    # Миграция 32→64 на проде — боль. Лучше сразу BIGINT.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#bigautofield
    default_auto_field = 'django.db.models.BigAutoField'

    # Полный Python-путь к пакету приложения.
    # Django использует это для:
    #   - поиска models.py / models/ внутри пакета
    #   - загрузки миграций из migrations/
    #   - построения db_table по умолчанию: orders_order
    #
    # ВАЖНО: должно совпадать с путём в INSTALLED_APPS.
    # 📖 https://docs.djangoproject.com/en/stable/ref/applications/#configuring-applications
    name = 'apps.orders'

    # Человекочитаемое название для Django admin и логов.
    verbose_name = 'Заказы'

    def ready(self):
        """
        Вызывается Django после загрузки всех моделей.

        Зачем: подключаем сигналы (signals.py) здесь, а не на уровне модуля.
        Причина: импорт signals на верхнем уровне models.py может вызвать
        circular import (signals → models → signals).

        Паттерн: AppConfig.ready() → import signals — стандарт Django.
        📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.ready
        """
        # Импортируем signals для регистрации обработчиков.
        # Используем __import__() для защиты от циклических импортов:
        #   если в signals.py есть from apps.orders.models import Order,
        #   то при ready() модели уже загружены — безопасно.
        # Но привычка использовать __import__() в ready() —
        # это defensive programming для больших проектов.
        import apps.orders.signals  # noqa: F401
