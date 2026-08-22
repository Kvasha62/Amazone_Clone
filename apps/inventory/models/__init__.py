# ────────────────────────────────────────────────────────────────────────
# apps/inventory/models/__init__.py — реэкспорт моделей склада.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • from apps.inventory.models import Stock → ImportError
#   • Django не обнаружит модели → миграции не создадутся
# ────────────────────────────────────────────────────────────────────────

from apps.inventory.models.stock import Stock
from apps.inventory.models.stock_movement import StockMovement

__all__ = [
    'Stock',
    'StockMovement',
]
