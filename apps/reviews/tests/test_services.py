# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_services.py
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from rest_framework.exceptions import ValidationError

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.reviews.models import Review
from apps.reviews.services.review_service import ReviewService
from apps.reviews.tests.factories import create_test_review


class CreateReviewServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()

    def test_create_review_success(self):
        review = ReviewService.create_review(
            user=self.user,
            product=self.product,
            rating=4,
            text='Отличный телефон, пользуюсь месяц!',
        )
        self.assertEqual(review.rating, 4)
        self.assertTrue(review.is_approved)
        self.assertFalse(review.verified_purchase)

    def test_create_review_updates_product_rating(self):
        ReviewService.create_review(
            user=self.user, product=self.product,
            rating=5, text='Очень понравился, рекомендую!',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('5.00'))
        self.assertEqual(self.product.reviews_count, 1)

    def test_create_review_avg_rating(self):
        user2 = create_test_user()
        ReviewService.create_review(
            user=self.user, product=self.product,
            rating=5, text='Очень понравился, рекомендую!',
        )
        ReviewService.create_review(
            user=user2, product=self.product,
            rating=3, text='Нормальный телефон за свои деньги.',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('4.00'))
        self.assertEqual(self.product.reviews_count, 2)

    def test_create_duplicate_review_fails(self):
        ReviewService.create_review(
            user=self.user, product=self.product,
            rating=5, text='Очень понравился, рекомендую!',
        )
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=3, text='Нормальный телефон за свои деньги.',
            )

    def test_create_review_rating_too_low(self):
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=0, text='Очень понравился, рекомендую!',
            )

    def test_create_review_rating_too_high(self):
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=6, text='Очень понравился, рекомендую!',
            )

    def test_create_review_text_too_short(self):
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=5, text='Ок',
            )


class UpdateReviewServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.review = create_test_review(
            self.user, self.product, rating=5,
            text='Очень понравился, рекомендую!',
        )

    def test_update_rating(self):
        review = ReviewService.update_review(
            self.review, user=self.user, rating=3,
        )
        self.assertEqual(review.rating, 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('3.00'))

    def test_update_text(self):
        review = ReviewService.update_review(
            self.review, user=self.user,
            text='Обновлённый текст отзыва после месяца использования.',
        )
        self.assertEqual(
            review.text,
            'Обновлённый текст отзыва после месяца использования.',
        )

    def test_update_wrong_user_fails(self):
        other_user = create_test_user()
        from rest_framework.exceptions import NotFound
        with self.assertRaises(NotFound):
            ReviewService.update_review(
                self.review, user=other_user, rating=1,
            )


class DeleteReviewServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.review = create_test_review(
            self.user, self.product, rating=5,
            text='Очень понравился, рекомендую!',
        )

    def test_delete_by_author(self):
        ReviewService.delete_review(self.review, user=self.user)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviews_count, 0)

    def test_delete_by_staff(self):
        staff = create_test_user(is_staff=True)
        ReviewService.delete_review(self.review, user=staff)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())

    def test_delete_by_other_user_fails(self):
        other = create_test_user()
        from rest_framework.exceptions import NotFound
        with self.assertRaises(NotFound):
            ReviewService.delete_review(self.review, user=other)


class ModerationServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.review = create_test_review(
            self.user, self.product, rating=1,
            text='Ужасный товар, не рекомендую.',
            is_approved=False,
        )

    def test_approve_review(self):
        review = ReviewService.approve_review(self.review)
        self.assertTrue(review.is_approved)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviews_count, 1)

    def test_reject_review(self):
        review = ReviewService.reject_review(self.review)
        self.assertFalse(review.is_approved)
