# ────────────────────────────────────────────────────────────────────────
# apps/analytics/models/__init__.py — реэкспорт моделей аналитики.
#
# ИМПОРТЫ:
#   from apps.analytics.models import ProductView
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
# ────────────────────────────────────────────────────────────────────────

from apps.analytics.models.product_view import ProductView

__all__ = ['ProductView']
