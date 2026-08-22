# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_models.py
# ────────────────────────────────────────────────────────────────────────

from django.db import IntegrityError
from django.test import TestCase

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.reviews.tests.factories import create_test_review


class ReviewModelTests(CatalogTestCase):
    """Тесты модели Review."""

    def setUp(self):
        self.user = create_test_user()

    def test_create_review(self):
        review = create_test_review(self.user, self.product)
        self.assertIsNotNone(review.pk)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_approved)

    def test_unique_user_product(self):
        """Один отзыв на товар от одного пользователя."""
        create_test_review(self.user, self.product)
        with self.assertRaises(IntegrityError):
            create_test_review(self.user, self.product)

    def test_different_users_same_product(self):
        """Разные пользователи могут оставлять отзывы на один товар."""
        user2 = create_test_user()
        create_test_review(self.user, self.product)
        review2 = create_test_review(user2, self.product)
        self.assertIsNotNone(review2.pk)

    def test_str_representation(self):
        review = create_test_review(self.user, self.product, rating=4)
        result = str(review)
        self.assertIn('★4', result)

    def test_helpful_score(self):
        review = create_test_review(self.user, self.product)
        review.helpful_yes = 10
        review.helpful_no = 3
        self.assertEqual(review.helpful_score, 7)

    def test_default_helpful_zero(self):
        review = create_test_review(self.user, self.product)
        self.assertEqual(review.helpful_yes, 0)
        self.assertEqual(review.helpful_no, 0)
