from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.tests.factories import create_test_user
from apps.catalog.tests.factories import CatalogTestCase
from apps.inventory.models import Stock
from apps.pricing.models import Price
from apps.wishlist.tests.factories import create_test_wishlist, create_test_wishlist_item


class WishlistListAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_empty(self):
        url = reverse('wishlist:wishlist-detail')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items_count'], 0)

    def test_get_with_items(self):
        wl = create_test_wishlist(self.user)
        create_test_wishlist_item(wl, self.variant_128)
        url = reverse('wishlist:wishlist-detail')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['items']), 1)

    def test_requires_auth(self):
        self.client.logout()
        url = reverse('wishlist:wishlist-detail')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class WishlistAddAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_add_success(self):
        url = reverse('wishlist:wishlist-add')
        resp = self.client.post(url, {
            'variant_id': self.variant_128.pk,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_add_duplicate(self):
        url = reverse('wishlist:wishlist-add')
        self.client.post(url, {'variant_id': self.variant_128.pk}, format='json')
        resp = self.client.post(url, {'variant_id': self.variant_128.pk}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_not_found_variant(self):
        url = reverse('wishlist:wishlist-add')
        resp = self.client.post(url, {'variant_id': 99999}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class WishlistRemoveAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.wl = create_test_wishlist(self.user)
        self.item = create_test_wishlist_item(self.wl, self.variant_128)

    def test_remove_success(self):
        url = reverse('wishlist:wishlist-remove', kwargs={'item_id': self.item.pk})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_remove_not_found(self):
        url = reverse('wishlist:wishlist-remove', kwargs={'item_id': 99999})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class WishlistMoveToCartAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.wl = create_test_wishlist(self.user)
        self.item = create_test_wishlist_item(self.wl, self.variant_128)
        Stock.objects.create(variant=self.variant_128, quantity=100)
        Price.objects.create(variant=self.variant_128, price=Decimal('50000.00'))

    def test_move_success(self):
        url = reverse('wishlist:wishlist-move-to-cart')
        resp = self.client.post(url, {
            'variant_id': self.variant_128.pk,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['moved'], 1)


class WishlistClearAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.wl = create_test_wishlist(self.user)
        create_test_wishlist_item(self.wl, self.variant_128)
        create_test_wishlist_item(self.wl, self.variant_256)

    def test_clear(self):
        url = reverse('wishlist:wishlist-clear')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['removed'], 2)
