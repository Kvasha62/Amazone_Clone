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
        # ARCH-001 Stage 2: здесь НЕТ ни cross-domain Django-сигналов,
        # ни регистрации слушателей/подписок — автоматическая реакция
        # pricing на изменение состояния каталога запрещена архитектурой
        # (ARCHITECTURE.md → Cross-Domain Coordination: единственный
        # механизм — явные service-вызовы с видимой точкой в коде).
        #
        # Обновление Product.min_price/max_price происходит ТОЛЬКО через
        # явные вызовы PricingService:
        #   set_price() / remove_price()          — изменение цены варианта
        #   set_variant_active(variant, is_active) — смена is_active
        #   delete_variant(variant)                — удаление варианта
        #   recalculate_product_bounds(product)    — прямой пересчёт
        # Направление зависимости: pricing → catalog (CatalogService).
        # ────────────────────────────────────────────────────────────
        pass
