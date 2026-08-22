# ────────────────────────────────────────────────────────────────────────
# apps/shipping/models/__init__.py — реэкспорт моделей доставки.
#
# Паттерн «package models»: вместо единого models.py используем
# директорию models/ с отдельными файлами для каждой модели.
#
# ИМПОРТЫ:
#   from apps.shipping.models import ShippingZone, ShippingMethod, Shipment
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • from apps.shipping.models import Shipment → ImportError
#   • Django не обнаружит модели → миграции не создадутся
# ────────────────────────────────────────────────────────────────────────

from apps.shipping.models.shipping_zone import ShippingZone
from apps.shipping.models.shipping_method import ShippingMethod
from apps.shipping.models.shipment import Shipment

__all__ = [
    'ShippingZone',
    'ShippingMethod',
    'Shipment',
]
