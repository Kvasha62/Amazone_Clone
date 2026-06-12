# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_querysets.py
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.reviews.models import Review
from apps.reviews.tests.factories import create_test_review


class ReviewQuerySetTests(CatalogTestCase):

    def setUp(self):
        self.user1 = create_test_user()
        self.user2 = create_test_user()

        self.review1 = create_test_review(
            self.user1, self.product, rating=5, is_approved=True,
        )
        self.review2 = create_test_review(
            self.user2, self.product, rating=2, is_approved=True,
            verified_purchase=True,
        )
        self.review3 = create_test_review(
            create_test_user(), self.product, rating=1, is_approved=False,
        )

    def test_approved(self):
        qs = Review.objects.approved()
        self.assertEqual(qs.count(), 2)

    def test_pending(self):
        qs = Review.objects.pending()
        self.assertEqual(qs.count(), 1)

    def test_for_product(self):
        qs = Review.objects.for_product(self.product)
        self.assertEqual(qs.count(), 3)

    def test_for_user(self):
        qs = Review.objects.for_user(self.user1)
        self.assertEqual(qs.count(), 1)

    def test_verified(self):
        qs = Review.objects.verified()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.review2.pk)

    def test_high_rated(self):
        qs = Review.objects.high_rated()
        self.assertEqual(qs.count(), 1)
        self.assertIn(self.review1, qs)

    def test_low_rated(self):
        qs = Review.objects.low_rated()
        # review2 (rating=2) и review3 (rating=1) — оба ≤ 2
        self.assertEqual(qs.count(), 2)

    def test_with_rating(self):
        qs = Review.objects.with_rating(5)
        self.assertEqual(qs.count(), 1)
