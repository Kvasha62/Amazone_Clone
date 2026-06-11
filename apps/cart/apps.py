from django.apps import AppConfig


class CartConfig(AppConfig):
    name = 'apps.cart'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Корзина'

    def ready(self):
        # Подключаем сигнал слияния гостевой корзины при session-логине.
        # Для JWT-авторизации слияние вызывается явно через POST /api/v1/cart/merge/.
        import apps.cart.signals  # noqa: F401
