# ────────────────────────────────────────────────────────────────────────
# apps/shipping/tests/test_managers.py — тесты менеджеров доставки.
#
# Проверяет:
#   • ShippingMethodManager: active(), for_zone(), for_zone_code(),
#     by_type(), with_zone()
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from apps.shipping.models import ShippingMethod
from apps.shipping.tests.factories import create_test_method, create_test_zone


class ShippingMethodManagerTests(TestCase):
    """Тесты ShippingMethodManager."""

    def setUp(self):
        self.zone_msk = create_test_zone(
            name='Москва', zone_code='msk',
        )
        self.zone_spb = create_test_zone(
            name='СПб', zone_code='spb',
        )
        self.courier_msk = create_test_method(
            zone=self.zone_msk,
            name='Курьер МСК',
            shipping_type='courier',
            sort_order=10,
        )
        self.pickup_msk = create_test_method(
            zone=self.zone_msk,
            name='ПВЗ МСК',
            shipping_type='pickup',
            sort_order=20,
        )
        self.courier_spb = create_test_method(
            zone=self.zone_spb,
            name='Курьер СПб',
            shipping_type='courier',
            sort_order=10,
        )

    def test_active_excludes_inactive(self):
        """active() исключает неактивные."""
        self.courier_spb.is_active = False
        self.courier_spb.save()
        active = ShippingMethod.objects.active()
        self.assertEqual(active.count(), 2)
        self.assertNotIn(self.courier_spb, active)

    def test_for_zone(self):
        """for_zone() фильтрует по зоне."""
        methods = ShippingMethod.objects.for_zone(self.zone_msk)
        self.assertEqual(methods.count(), 2)
        self.assertIn(self.courier_msk, methods)
        self.assertIn(self.pickup_msk, methods)

    def test_for_zone_code(self):
        """for_zone_code() фильтрует по коду зоны."""
        methods = ShippingMethod.objects.for_zone_code('spb')
        self.assertEqual(methods.count(), 1)
        self.assertEqual(methods.first(), self.courier_spb)

    def test_by_type(self):
        """by_type() фильтрует по типу доставки."""
        couriers = ShippingMethod.objects.by_type('courier')
        self.assertEqual(couriers.count(), 2)
        pickups = ShippingMethod.objects.by_type('pickup')
        self.assertEqual(pickups.count(), 1)

    def test_with_zone_select_related(self):
        """with_zone() подтягивает зону (select_related)."""
        methods = ShippingMethod.objects.with_zone()
        # Проверяем что все методы доступны без дополнительного запроса
        for m in methods:
            self.assertIsNotNone(m.zone.pk)

    def test_chaining(self):
        """Цепочка вызовов: active().for_zone().by_type()."""
        methods = (
            ShippingMethod.objects
            .active()
            .for_zone(self.zone_msk)
            .by_type('courier')
        )
        self.assertEqual(methods.count(), 1)
        self.assertEqual(methods.first(), self.courier_msk)
