# ────────────────────────────────────────────────────────────────────────
# PROD-002 regression: concurrency-sensitive Admin fields are read-only.
#
# Django default ModelAdmin would allow direct ORM writes of FSM / stock /
# price / coupon counters. These guards force operators onto Service Layer
# entrypoints (or explicit Admin actions that already call services).
# ────────────────────────────────────────────────────────────────────────

from django.contrib.admin.sites import AdminSite
from django.test import SimpleTestCase

from apps.discounts.admin.coupon_admin import CouponAdmin
from apps.discounts.models import Coupon
from apps.inventory.admin.stock_admin import StockAdmin
from apps.inventory.models import Stock
from apps.notifications.admin.notification_admin import NotificationAdmin
from apps.notifications.models import Notification
from apps.orders.admin.order_admin import OrderAdmin
from apps.orders.models import Order
from apps.pricing.admin.price_admin import PriceAdmin
from apps.pricing.models import Price
from apps.shipping.admin.shipping_admin import ShipmentAdmin
from apps.shipping.models import Shipment


class AdminMutationGuardTests(SimpleTestCase):
    def setUp(self):
        self.site = AdminSite()

    def test_order_status_readonly(self):
        admin = OrderAdmin(Order, self.site)
        self.assertIn('status', admin.readonly_fields)

    def test_shipment_status_and_cost_readonly(self):
        admin = ShipmentAdmin(Shipment, self.site)
        for field in ('status', 'shipping_cost', 'shipped_at', 'delivered_at'):
            self.assertIn(field, admin.readonly_fields)

    def test_stock_quantity_readonly(self):
        admin = StockAdmin(Stock, self.site)
        for field in ('quantity', 'reserved_quantity'):
            self.assertIn(field, admin.readonly_fields)

    def test_price_amounts_readonly(self):
        admin = PriceAdmin(Price, self.site)
        for field in ('price', 'sale_price', 'currency', 'variant'):
            self.assertIn(field, admin.readonly_fields)

    def test_coupon_times_used_readonly(self):
        admin = CouponAdmin(Coupon, self.site)
        self.assertIn('times_used', admin.readonly_fields)

    def test_notification_status_readonly(self):
        admin = NotificationAdmin(Notification, self.site)
        for field in ('status', 'sent_at', 'read_at'):
            self.assertIn(field, admin.readonly_fields)
