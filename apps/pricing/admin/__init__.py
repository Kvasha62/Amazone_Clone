# ────────────────────────────────────────────────────────────────────────
# apps/pricing/admin/__init__.py — реэкспорт admin-классов pricing.
# ────────────────────────────────────────────────────────────────────────

from apps.pricing.admin.price_admin import PriceAdmin, PriceHistoryAdmin

__all__ = ['PriceAdmin', 'PriceHistoryAdmin']
