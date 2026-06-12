# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_api.py
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.reviews.tests.factories import create_test_review


class ReviewListAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.url = reverse('reviews:review-list')

    def test_list_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_review(self):
        self.client.force_authenticate(self.user)
        data = {
            'product_id': self.product.pk,
            'rating': 4,
            'text': 'Отличный телефон, пользуюсь месяц!',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['rating'], 4)

    def test_create_duplicate_fails(self):
        self.client.force_authenticate(self.user)
        data = {
            'product_id': self.product.pk,
            'rating': 4,
            'text': 'Отличный телефон, пользуюсь месяц!',
        }
        self.client.post(self.url, data, format='json')
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_invalid_product(self):
        self.client.force_authenticate(self.user)
        data = {
            'product_id': 99999,
            'rating': 5,
            'text': 'Отличный телефон, пользуюсь месяц!',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_user_reviews(self):
        self.client.force_authenticate(self.user)
        create_test_review(self.user, self.product)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_list_by_product(self):
        self.client.force_authenticate(self.user)
        create_test_review(self.user, self.product)
        resp = self.client.get(self.url, {'product_id': self.product.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class ReviewDetailAPITests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.review = create_test_review(
            self.user, self.product, rating=4,
            text='Отличный телефон, пользуюсь месяц!',
        )

    def test_get_detail(self):
        self.client.force_authenticate(self.user)
        url = reverse('reviews:review-detail', kwargs={'review_id': self.review.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['rating'], 4)

    def test_update_review(self):
        self.client.force_authenticate(self.user)
        url = reverse('reviews:review-detail', kwargs={'review_id': self.review.pk})
        resp = self.client.patch(url, {'rating': 3}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['rating'], 3)

    def test_update_wrong_user(self):
        other = create_test_user()
        self.client.force_authenticate(other)
        url = reverse('reviews:review-detail', kwargs={'review_id': self.review.pk})
        resp = self.client.patch(url, {'rating': 1}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_review(self):
        self.client.force_authenticate(self.user)
        url = reverse('reviews:review-detail', kwargs={'review_id': self.review.pk})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
