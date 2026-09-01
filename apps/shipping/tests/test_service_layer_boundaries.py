# ────────────────────────────────────────────────────────────────────────
# PROD-002 regression: stale shipment cleanup via ShippingService FSM.
# ────────────────────────────────────────────────────────────────────────

import inspect
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.orders.models.order import OrderStatus
from apps.orders.tests.factories import create_test_order
from apps.shipping.admin.shipping_admin import ShipmentAdmin
from apps.shipping.constants import SHIPMENT_PREPARING, SHIPMENT_RETURNED
from apps.shipping.management.commands import cleanup_stale_shipments as cleanup_cmd
from apps.shipping.models import Shipment
from apps.shipping.services.shipping_service import ShippingService
from apps.shipping.tests.factories import create_test_method, create_test_shipment



class StaleShipmentSourceBoundaryTests(SimpleTestCase):
    def test_cleanup_command_delegates_to_service(self):
        source = inspect.getsource(cleanup_cmd.Command.handle)
        self.assertIn('ShippingService.return_stale_preparing', source)
        self.assertNotIn('.save(', source)
        self.assertNotIn("status = 'returned'", source)

    def test_return_stale_uses_transition_status(self):
        source = inspect.getsource(ShippingService.return_stale_preparing)
        self.assertIn('transition_status', source)


class StaleShipmentBehaviorTests(TestCase):
    def setUp(self):
        from apps.orders.tests.factories import create_test_user

        self.user = create_test_user()
        # CONFIRMED so RETURNED can cancel via OrderService without extra setup.
        self.order = create_test_order(self.user, status=OrderStatus.CONFIRMED)
        self.method = create_test_method()
        self.shipment = create_test_shipment(
            order=self.order,
            method=self.method,
            status=SHIPMENT_PREPARING,
            shipping_cost=Decimal('300.00'),
        )
        Shipment.objects.filter(pk=self.shipment.pk).update(
            updated_at=timezone.now() - timedelta(hours=72),
        )
        self.shipment.refresh_from_db()

    def test_return_stale_preparing_transitions_via_fsm(self):
        # Avoid deep inventory side-effects from OrderService.cancel on RETURNED.
        with patch.object(
            ShippingService,
            '_sync_order_status',
            return_value=None,
        ):
            result = ShippingService.return_stale_preparing(hours=48, dry_run=False)
        self.assertEqual(result['updated'], 1)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, SHIPMENT_RETURNED)

    def test_cleanup_command_uses_service_path(self):
        with patch.object(
            ShippingService,
            '_sync_order_status',
            return_value=None,
        ):
            cleanup_cmd.Command().handle(hours=48, dry_run=False)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, SHIPMENT_RETURNED)

    def test_dry_run_does_not_mutate(self):
        result = ShippingService.return_stale_preparing(hours=48, dry_run=True)
        self.assertEqual(result['candidates'], 1)
        self.assertEqual(result['updated'], 0)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, SHIPMENT_PREPARING)

    def test_shipment_admin_status_is_readonly(self):
        admin = ShipmentAdmin(Shipment, AdminSite())
        self.assertIn('status', admin.readonly_fields)
        self.assertIn('shipping_cost', admin.readonly_fields)
