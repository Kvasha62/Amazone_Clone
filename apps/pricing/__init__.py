# ────────────────────────────────────────────────────────────────────────
# apps/pricing/__init__.py — конфигурация приложения «Ценообразование».
#
# Модуль отвечает за:
#   • Актуальные цены вариантов товара (Price — OneToOne к ProductVariant)
#   • Историю изменений цен (PriceHistory — FK к ProductVariant)
#   • Денормализацию min_price / max_price на Product
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • INSTALLED_APPS не найдёт apps.pricing → таблицы не создадутся
#   • Сигналы пересчёта min/max не подключатся → цены на товаре устареют
# ────────────────────────────────────────────────────────────────────────

from django.apps import AppConfig


class PricingConfig(AppConfig):
    """
    Конфигурация модуля ценообразования.

    ready() — подключает сигнал пересчёта Product.min_price/max_price
    при сохранении/удалении Price.

    📖 https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.ready
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pricing'
    verbose_name = 'Ценообразование'

    def ready(self):
        """
        Подключает signals.py → @receiver(post_save/post_delete, sender=Price).
        При изменении цены → пересчитываются Product.min_price / max_price.
        """
        import apps.pricing.signals  # noqa: F401
