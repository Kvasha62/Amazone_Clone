# ────────────────────────────────────────────────────────────────────────
# apps/inventory/tests/factories.py — фабрики для тестов склада.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
# ────────────────────────────────────────────────────────────────────────

from apps.inventory.constants import LOW_STOCK_THRESHOLD
from apps.inventory.models import Stock, StockMovement
from apps.inventory.models.stock_movement import MovementKind


def create_test_stock(variant, quantity: int = 100, **kwargs):
    """Создаёт тестовый Stock для варианта."""
    defaults = {
        'quantity': quantity,
        'reserved_quantity': 0,
        'low_stock_threshold': LOW_STOCK_THRESHOLD,
    }
    defaults.update(kwargs)
    return Stock.objects.create(variant=variant, **defaults)


def create_test_movement(stock, kind=MovementKind.IN, delta=10, **kwargs):
    """Создаёт тестовое StockMovement."""
    defaults = {
        'quantity_before': stock.quantity,
        'quantity_after': stock.quantity + delta,
        'note': 'Test movement',
    }
    defaults.update(kwargs)
    return StockMovement.objects.create(
        stock=stock, kind=kind, delta=delta, **defaults,
    )
