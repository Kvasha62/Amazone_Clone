# ────────────────────────────────────────────────────────────────────────
# apps/pricing/__init__.py — конфигурация приложения «Ценообразование».
#
# Модуль отвечает за:
#   • Актуальные цены вариантов товара (Price — OneToOne к ProductVariant)
#   • Историю изменений цен (PriceHistory — FK к ProductVariant)
#
# ARCH-001 (Pricing → Catalog ownership):
#   Пересчёт денормализованных Product.min_price / max_price ПЕРЕМЕЩЁН
#   в bounded context `catalog` (см. apps.catalog.services.CatalogService).
#   Здесь больше НЕТ cross-domain сигналов на пересчёт цен товара.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
# ────────────────────────────────────────────────────────────────────────

from django.apps import AppConfig


class PricingConfig(AppConfig):
    """
    Конфигурация модуля ценообразования.

    Обновление денормализованных цен товара выполняется через
    CatalogService.recalculate_product_prices() (см. ARCH-001).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pricing'
    verbose_name = 'Ценообразование'

    def ready(self):
        # ARCH-001: cross-domain сигналы на пересчёт Product.min_price/max_price
        # удалены. Цены товара обновляет только каталог своим сервисом.
        pass
