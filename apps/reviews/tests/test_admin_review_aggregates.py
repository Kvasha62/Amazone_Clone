"""ARCH-001 H2 — ReviewAdmin must preserve Product review aggregates.

ReviewAdmin can mutate Review rows, but operations that affect
``Product.rating`` / ``Product.reviews_count`` must go through the existing
ReviewService path:

    ReviewService.<create/update/delete/approve/reject>()
        → ReviewService.recalculate_product_rating()
        → CatalogService.set_review_stats()

These tests exercise Django Admin behavior (change form, add form, actions,
delete hooks) and direct ``ModelAdmin`` hook calls so ``readonly_fields`` alone
cannot hide a still-vulnerable save path.
"""
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.catalog.constants import ProductStatus
from apps.catalog.models import Brand, Category, Product
from apps.orders.tests.factories import create_test_user
from apps.reviews.admin.review_admin import (
    REVIEW_ADMIN_IMMUTABLE_CHANGE_FIELDS,
    REVIEW_AGGREGATE_SOURCE_FIELDS,
    ReviewAdmin,
)
from apps.reviews.models import Review
from apps.reviews.services.review_service import ReviewService
from apps.reviews.tests.factories import create_test_review

User = get_user_model()

REVIEW_TEXT = 'Очень полезный отзыв о товаре после месяца использования.'
UPDATED_REVIEW_TEXT = 'Обновлённый текст отзыва после дополнительной проверки.'


class ReviewAdminAggregateTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='reviewadmin',
            email='reviewadmin@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        cls.brand = Brand.objects.create(name='ReviewAdminBrand')
        cls.category = Category.add_root(name='ReviewAdminCat')
        cls.product = Product.objects.create(
            name='Review Admin Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.other_product = Product.objects.create(
            name='Other Review Admin Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.author = create_test_user(email='review-author@test.com')
        cls.other_author = create_test_user(email='other-review-author@test.com')

    def setUp(self):
        self.site = AdminSite()
        self.admin = ReviewAdmin(Review, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/reviews/review/')
        self.request.user = self.staff

    def _request_with_messages(self):
        request = self.factory.post('/admin/reviews/review/')
        request.user = self.staff
        request.session = self.client.session
        setattr(request, '_messages', FallbackStorage(request))
        return request

    def _review_change_data(self, review, **overrides):
        data = {
            # Included deliberately: new Admin treats these as read-only and
            # ignores the payload, while the pre-H2 form accepted them.
            # This keeps regression tests focused on the save path instead of
            # failing early on missing required raw-id fields under old code.
            'user': str(review.user_id),
            'product': str(review.product_id),
            'rating': str(review.rating),
            'title': review.title,
            'text': review.text,
            'helpful_yes': str(review.helpful_yes),
            'helpful_no': str(review.helpful_no),
        }
        if review.verified_purchase:
            data['verified_purchase'] = 'on'
        if review.is_approved:
            data['is_approved'] = 'on'
        data.update(overrides)
        return data

    def _review_add_data(self, **overrides):
        data = {
            'user': str(self.author.pk),
            'product': str(self.product.pk),
            'rating': '4',
            'title': 'Admin-created review',
            'text': REVIEW_TEXT,
            'helpful_yes': '0',
            'helpful_no': '0',
            'is_approved': 'on',
        }
        data.update(overrides)
        return data

    def _assert_product_stats(self, product, *, rating, reviews_count):
        product.refresh_from_db()
        self.assertEqual(product.rating, Decimal(rating))
        self.assertEqual(product.reviews_count, reviews_count)


class ReviewAdminConfigurationTests(ReviewAdminAggregateTestCase):
    def test_existing_review_cannot_be_moved_between_user_or_product_fields(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )

        form_class = self.admin.get_form(self.request, obj=review, change=True)
        form_fields = form_class(instance=review).fields

        self.assertEqual(
            ('product', 'rating', 'is_approved'),
            REVIEW_AGGREGATE_SOURCE_FIELDS,
        )
        for field in REVIEW_ADMIN_IMMUTABLE_CHANGE_FIELDS:
            self.assertNotIn(field, form_fields)
        self.assertIn('rating', form_fields)
        self.assertIn('is_approved', form_fields)

    def test_new_review_still_accepts_user_product_and_rating(self):
        form_class = self.admin.get_form(self.request, obj=None, change=False)
        form_fields = form_class().fields

        self.assertIn('user', form_fields)
        self.assertIn('product', form_fields)
        self.assertIn('rating', form_fields)


class ReviewAdminSavePathTests(ReviewAdminAggregateTestCase):
    def test_admin_add_review_recalculates_product_aggregates(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            '/admin/reviews/review/add/',
            self._review_add_data(rating='4'),
        )

        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(user=self.author, product=self.product)
        self.assertEqual(review.rating, 4)
        self.assertTrue(review.is_approved)
        self._assert_product_stats(
            self.product, rating='4.00', reviews_count=1,
        )

    def test_admin_add_unapproved_review_does_not_count_product_aggregate(self):
        self.client.force_login(self.staff)

        data = self._review_add_data()
        data.pop('is_approved')
        response = self.client.post('/admin/reviews/review/add/', data)

        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(user=self.author, product=self.product)
        self.assertFalse(review.is_approved)
        self._assert_product_stats(
            self.product, rating='0.00', reviews_count=0,
        )

    def test_admin_change_rating_recalculates_product_aggregates(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)
        self.client.force_login(self.staff)

        response = self.client.post(
            f'/admin/reviews/review/{review.pk}/change/',
            self._review_change_data(review, rating='3'),
        )

        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.rating, 3)
        self._assert_product_stats(self.product, rating='3.00', reviews_count=1)

    def test_save_model_rating_change_recalculates_product_aggregates(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        changed = Review.objects.get(pk=review.pk)
        changed.rating = 2

        self.admin.save_model(self.request, changed, form=None, change=True)

        review.refresh_from_db()
        self.assertEqual(review.rating, 2)
        self._assert_product_stats(self.product, rating='2.00', reviews_count=1)

    def test_admin_change_approval_recalculates_product_aggregates(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)
        self.client.force_login(self.staff)

        data = self._review_change_data(review)
        data.pop('is_approved')
        response = self.client.post(
            f'/admin/reviews/review/{review.pk}/change/',
            data,
        )

        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertFalse(review.is_approved)
        self._assert_product_stats(self.product, rating='0.00', reviews_count=0)

    def test_admin_change_text_still_works_without_changing_aggregates(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=4,
            text=REVIEW_TEXT,
        )
        self._assert_product_stats(self.product, rating='4.00', reviews_count=1)
        self.client.force_login(self.staff)

        response = self.client.post(
            f'/admin/reviews/review/{review.pk}/change/',
            self._review_change_data(review, text=UPDATED_REVIEW_TEXT),
        )

        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.text, UPDATED_REVIEW_TEXT)
        self._assert_product_stats(self.product, rating='4.00', reviews_count=1)

    def test_save_model_rejects_existing_review_product_move(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        moved = Review.objects.get(pk=review.pk)
        moved.product = self.other_product

        with self.assertRaises(PermissionDenied):
            self.admin.save_model(self.request, moved, form=None, change=True)

        review.refresh_from_db()
        self.assertEqual(review.product_id, self.product.pk)
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)
        self._assert_product_stats(self.other_product, rating='0.00', reviews_count=0)

    def test_save_model_rejects_existing_review_user_move(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        moved = Review.objects.get(pk=review.pk)
        moved.user = self.other_author

        with self.assertRaises(PermissionDenied):
            self.admin.save_model(self.request, moved, form=None, change=True)

        review.refresh_from_db()
        self.assertEqual(review.user_id, self.author.pk)
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)


class ReviewAdminDeletePathTests(ReviewAdminAggregateTestCase):
    def test_admin_single_delete_recalculates_product_aggregates(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)

        self.admin.delete_model(self.request, review)

        self.assertFalse(Review.objects.filter(pk=review.pk).exists())
        self._assert_product_stats(self.product, rating='0.00', reviews_count=0)

    def test_admin_bulk_delete_recalculates_product_aggregates(self):
        review_a = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        review_b = ReviewService.create_review(
            self.other_author,
            self.product,
            rating=3,
            text='Второй подробный отзыв для массового удаления.',
        )
        self._assert_product_stats(self.product, rating='4.00', reviews_count=2)

        self.admin.delete_queryset(
            self.request,
            Review.objects.filter(pk__in=[review_a.pk, review_b.pk]),
        )

        self.assertFalse(
            Review.objects.filter(pk__in=[review_a.pk, review_b.pk]).exists(),
        )
        self._assert_product_stats(self.product, rating='0.00', reviews_count=0)


class ReviewAdminActionTests(ReviewAdminAggregateTestCase):
    def test_approve_action_recalculates_product_aggregates(self):
        review = create_test_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
            is_approved=False,
        )
        self._assert_product_stats(self.product, rating='0.00', reviews_count=0)

        self.admin.approve_selected(
            self._request_with_messages(),
            Review.objects.filter(pk=review.pk),
        )

        review.refresh_from_db()
        self.assertTrue(review.is_approved)
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)

    def test_reject_action_recalculates_product_aggregates(self):
        review = ReviewService.create_review(
            self.author,
            self.product,
            rating=5,
            text=REVIEW_TEXT,
        )
        self._assert_product_stats(self.product, rating='5.00', reviews_count=1)

        self.admin.reject_selected(
            self._request_with_messages(),
            Review.objects.filter(pk=review.pk),
        )

        review.refresh_from_db()
        self.assertFalse(review.is_approved)
        self._assert_product_stats(self.product, rating='0.00', reviews_count=0)
