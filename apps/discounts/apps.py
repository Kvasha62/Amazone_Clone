from django.apps import AppConfig


class DiscountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.discounts'
    verbose_name = 'Промокоды и скидки'

    def ready(self):
        import apps.discounts.signals  # noqa: F401
