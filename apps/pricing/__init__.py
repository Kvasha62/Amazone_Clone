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
#   (is_active, удаление варианта) каталог уведомляет слушателей через
#   контракт notify_price_relevant_state_changed(); pricing подписывается
#   на него в PricingConfig.ready() (apps/pricing/apps.py,
#   register_price_bounds_listener) — снова без Django-сигналов между
#   контекстами и без импорта pricing из catalog.
#
# AppConfig (PricingConfig) живёт в apps/pricing/apps.py — Django ≥ 4.1
# автоматически использует AppConfig-класс именно из модуля apps.py.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/applications/
# ────────────────────────────────────────────────────────────────────────
