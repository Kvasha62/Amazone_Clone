import logging
import logging.handlers

from django.test import TestCase
from apps.orders.tests.factories import create_test_user
from apps.wishlist.services.wishlist_service import WishlistService


class WishlistSignalTests(TestCase):

    def test_signal_on_create(self):
        user = create_test_user()
        with self.assertLogs('apps.wishlist.signals', level='INFO') as cm:
            WishlistService.get_or_create(user)
        self.assertTrue(
            any('wishlist_created_signal' in m for m in cm.output)
        )
