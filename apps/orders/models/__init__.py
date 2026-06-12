# ────────────────────────────────────────────────────────────────────────
# apps/orders/models/__init__.py — реэкспорт моделей заказа.
#
# Паттерн «package models»: вместо единого models.py используем
# директорию models/ с отдельными файлами для каждой модели.
#
# ПРЕИМУЩЕСТВА:
#   • Каждый файл фокусируется на одной модели → < 300 строк
#   • Модели можно импортировать: from apps.orders.models import Order
#   • Django автоматически находит models/ и регистрирует все модели
#
# ОСТОРОЖНО — циклические импорты:
#   Order → OrderItem (FK) — это однонаправленная связь, цикла нет.
#   Но если добавить метод OrderItem.get_order() → Order → нужен lazy import.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • from apps.orders.models import Order → ImportError
#   • Django не обнаружит модели → миграции не создадутся
# ────────────────────────────────────────────────────────────────────────

from apps.orders.models.order import Order
from apps.orders.models.order_item import OrderItem

__all__ = [
    'Order',
    'OrderItem',
]
