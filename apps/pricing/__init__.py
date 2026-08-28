# ────────────────────────────────────────────────────────────────────────
# apps/pricing/__init__.py — конфигурация приложения «Ценообразование».
#
# Модуль отвечает за:
#   • Актуальные цены вариантов товара (Price — OneToOne к ProductVariant)
#   • Историю изменений цен (PriceHistory — FK к ProductVariant)
#
# ARCH-001 (Pricing → Catalog ownership):
#   Расчёт денормализованных Product.min_price / max_price — ответственность
#   `pricing`. PricingService рассчитывает границы из своих цен (Price) и
#   передаёт готовые значения в публичный контракт каталога
#   CatalogService.set_product_prices(product, min_price=..., max_price=...).
#   `catalog` НЕ читает цены из pricing → зависимость однонаправленная
#   (pricing → catalog → catalog.Product). Здесь нет cross-domain сигналов.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
# ────────────────────────────────────────────────────────────────────────

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
        # ARCH-001: cross-domain сигналы на пересчёт Product.min_price/max_price
        # удалены. Цены товара обновляет только каталог своим сервисом.
        pass
