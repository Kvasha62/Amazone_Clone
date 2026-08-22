# ────────────────────────────────────────────────────────────────────────
# apps/pricing/services/__init__.py — реэкспорт сервисов ценообразования.
# ────────────────────────────────────────────────────────────────────────

from apps.pricing.services.pricing_service import PricingService

__all__ = ['PricingService']
