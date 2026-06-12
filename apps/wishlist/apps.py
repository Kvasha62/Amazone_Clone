from django.apps import AppConfig


class WishlistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.wishlist'
    verbose_name = 'Избранное'

    def ready(self):
        import apps.wishlist.signals  # noqa: F401
