from django.test import TestCase
from apps.orders.tests.factories import create_test_user
from apps.catalog.tests.factories import CatalogTestCase
from apps.wishlist.tests.factories import create_test_wishlist, create_test_wishlist_item


class WishlistModelTests(CatalogTestCase):

    def test_create_wishlist(self):
        user = create_test_user()
        wl = create_test_wishlist(user)
        self.assertIsNotNone(wl.pk)
        self.assertEqual(wl.user, user)
        self.assertEqual(wl.items_count, 0)

    def test_str(self):
        user = create_test_user()
        wl = create_test_wishlist(user)
        self.assertIn(str(user.pk), str(wl))

    def test_one_to_one(self):
        user = create_test_user()
        create_test_wishlist(user)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            create_test_wishlist(user)


class WishlistItemModelTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.wl = create_test_wishlist(self.user)

    def test_create_item(self):
        item = create_test_wishlist_item(self.wl, self.variant_128)
        self.assertIsNotNone(item.pk)
        self.assertEqual(item.wishlist, self.wl)
        self.assertEqual(item.variant, self.variant_128)

    def test_unique_constraint(self):
        create_test_wishlist_item(self.wl, self.variant_128)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            create_test_wishlist_item(self.wl, self.variant_128)

    def test_same_variant_different_wishlists(self):
        """Один и тот же вариант в разных списках — OK."""
        user2 = create_test_user()
        wl2 = create_test_wishlist(user2)
        create_test_wishlist_item(self.wl, self.variant_128)
        item2 = create_test_wishlist_item(wl2, self.variant_128)
        self.assertIsNotNone(item2.pk)
