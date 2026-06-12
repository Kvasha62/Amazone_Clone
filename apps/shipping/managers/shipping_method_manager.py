# ────────────────────────────────────────────────────────────────────────
# apps/shipping/managers/shipping_method_manager.py — менеджер способов доставки.
#
# Добавляет QuerySet-методы для фильтрации активных способов,
# способов для конкретной зоны и типа.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/
# ────────────────────────────────────────────────────────────────────────

from django.db import models


class ShippingMethodQuerySet(models.QuerySet):
    """
    Расширенный QuerySet для ShippingMethod.
    """

    def active(self):
        """Только активные способы доставки."""
        return self.filter(is_active=True)

    def for_zone(self, zone):
        """Способы доставки для конкретной зоны."""
        return self.filter(zone=zone)

    def for_zone_code(self, zone_code: str):
        """Способы доставки по коду зоны."""
        return self.filter(zone__zone_code=zone_code)

    def by_type(self, shipping_type: str):
        """Способы доставки определённого типа."""
        return self.filter(shipping_type=shipping_type)

    def with_zone(self):
        """Подтягивает зону (select_related)."""
        return self.select_related('zone')


class ShippingMethodManager(models.Manager):
    """
    Кастомный менеджер для ShippingMethod.
    """

    def get_queryset(self):
        return ShippingMethodQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def for_zone(self, zone):
        return self.get_queryset().for_zone(zone)

    def for_zone_code(self, zone_code: str):
        return self.get_queryset().for_zone_code(zone_code)

    def by_type(self, shipping_type: str):
        return self.get_queryset().by_type(shipping_type)

    def with_zone(self):
        return self.get_queryset().with_zone()
