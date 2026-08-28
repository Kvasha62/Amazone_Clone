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
# ARCH-001 Stage 2: при price-relevant изменении вариантов каталога
#   (is_active, удаление варианта) автоматической реакции НЕТ — она
#   невозможна без нарушения архитектуры (reverse dependency /
#   cross-context signal / event registry). Используются явные
#   service-вызовы (ARCHITECTURE.md → Cross-Domain Coordination):
#   PricingService.set_variant_active() / delete_variant() /
#   recalculate_product_bounds(). Направление зависимости — только
#   pricing → catalog.
#
# AppConfig (PricingConfig) живёт в apps/pricing/apps.py — Django ≥ 4.1
# автоматически использует AppConfig-класс именно из модуля apps.py.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
# ────────────────────────────────────────────────────────────────────────
