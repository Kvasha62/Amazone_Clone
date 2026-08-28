# ==============================================================================
# apps/pricing/apps.py — Конфигурация приложения «pricing».
#
# ВАЖНО (Django ≥ 4.1): AppConfig должен жить в apps.py — именно этот
# модуль Django автоматически сканирует при загрузке INSTALLED_APPS.
# Класс в __init__.py автоматически НЕ подхватывается.
# ==============================================================================

from django.apps import AppConfig


class PricingConfig(AppConfig):
    """
    Конфигурация модуля ценообразования.

    Расчёт денормализованных цен товара выполняется в `pricing`
    (PricingService), а запись в `catalog.Product` — через публичный
    контракт CatalogService.set_product_prices() (см. ARCH-001).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pricing'
    verbose_name = 'Ценообразование'

    def ready(self):
        # ────────────────────────────────────────────────────────────
        # ARCH-001 Stage 2: подписка pricing на price-relevant события
        # каталога (изменение is_active варианта, удаление варианта).
        #
        # Это НЕ Django signal и НЕ cross-domain сигнал:
        #   • каталог объявляет контракт register_price_bounds_listener();
        #   • pricing САМ (здесь, в своём AppConfig) регистрирует колбэк;
        #   • направление статических импортов — только pricing → catalog
        #     (catalog не импортирует pricing);
        #   • обработка синхронная, в том же потоке и транзакции, что и
        #     изменение состояния варианта.
        # ────────────────────────────────────────────────────────────
        from apps.catalog.services.catalog_service import (
            register_price_bounds_listener,
        )
        from apps.pricing.services.pricing_service import PricingService

        register_price_bounds_listener(PricingService.recalculate_product_bounds)
