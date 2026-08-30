"""ARCH-001 H2 — ProductAdmin must not edit review aggregates.

``Product.rating`` / ``Product.reviews_count`` are review-derived
aggregate fields. The service-level write path is

    ReviewService.recalculate_product_rating()
        → CatalogService.set_review_stats(product, rating, reviews_count)
        → Product.rating / Product.reviews_count

ProductAdmin may display these values, but it must not become a second
writer. The tests cover the generated Django Admin form and the server-side
``save_model`` defense-in-depth path.
"""
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.catalog.admin.product_admin import (
    PRODUCT_REVIEW_AGGREGATE_FIELDS,
    ProductAdmin,
)
from apps.catalog.constants import ProductStatus
from apps.catalog.models import Brand, Category, Product
from apps.catalog.services.catalog_service import CatalogService
from apps.orders.tests.factories import create_test_user
from apps.reviews.services.review_service import ReviewService

User = get_user_model()


class ProductAdminReviewAggregateReadOnlyTests(TestCase):
    """rating / reviews_count must not be ordinary ProductAdmin inputs."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='reviewstatsadmin',
            email='reviewstatsadmin@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        cls.brand = Brand.objects.create(name='ReviewStatsBrand')
        cls.category = Category.add_root(name='ReviewStatsCat')
        cls.product = Product.objects.create(
            name='Review Stats Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        CatalogService.set_review_stats(
            cls.product,
            rating=Decimal('4.50'),
            reviews_count=2,
        )
        cls.product.refresh_from_db()

    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/catalog/product/')
        self.request.user = self.staff

    def test_review_aggregate_fields_are_declared_readonly(self):
        self.assertEqual(
            ('rating', 'reviews_count'), PRODUCT_REVIEW_AGGREGATE_FIELDS,
        )
        for field in PRODUCT_REVIEW_AGGREGATE_FIELDS:
            self.assertIn(field, self.admin.readonly_fields)

    def test_change_form_has_no_review_aggregate_inputs(self):
        form_class = self.admin.get_form(
            self.request, obj=self.product, change=True,
        )
        form_fields = form_class(instance=self.product).fields
        for field in PRODUCT_REVIEW_AGGREGATE_FIELDS:
            self.assertNotIn(field, form_fields)

    def test_add_form_has_no_review_aggregate_inputs(self):
        form_class = self.admin.get_form(self.request, obj=None, change=False)
        form_fields = form_class().fields
        for field in PRODUCT_REVIEW_AGGREGATE_FIELDS:
            self.assertNotIn(field, form_fields)

    def test_change_page_renders_review_aggregates_as_readonly_text(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            f'/admin/catalog/product/{self.product.pk}/change/',
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('4.50', content)
        self.assertIn('2', content)
        self.assertNotIn('name="rating"', content)
        self.assertNotIn('name="reviews_count"', content)


class ProductAdminReviewAggregateGuardTests(TestCase):
    """Forced ProductAdmin saves must not persist review aggregates."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='reviewstatsguard',
            email='reviewstatsguard@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        cls.brand = Brand.objects.create(name='ReviewStatsGuardBrand')
        cls.category = Category.add_root(name='ReviewStatsGuardCat')
        cls.product = Product.objects.create(
            name='Review Stats Guard Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        CatalogService.set_review_stats(
            cls.product,
            rating=Decimal('4.00'),
            reviews_count=3,
        )
        cls.product.refresh_from_db()

    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/catalog/product/')
        self.request.user = self.staff

    def _assert_review_stats_unchanged(self, rating, reviews_count):
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, rating)
        self.assertEqual(self.product.reviews_count, reviews_count)

    def test_save_model_rejects_rating_change(self):
        before_rating = self.product.rating
        before_count = self.product.reviews_count
        self.product.rating = Decimal('1.00')

        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, self.product, form=None, change=True,
            )

        self._assert_review_stats_unchanged(before_rating, before_count)

    def test_save_model_rejects_reviews_count_change(self):
        before_rating = self.product.rating
        before_count = self.product.reviews_count
        self.product.reviews_count = 99

        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, self.product, form=None, change=True,
            )

        self._assert_review_stats_unchanged(before_rating, before_count)

    def test_save_model_rejects_review_aggregates_on_add(self):
        new_product = Product(
            name='Forced Review Stats Product',
            brand=self.brand,
            primary_category=self.category,
            status=ProductStatus.DRAFT,
            rating=Decimal('5.00'),
            reviews_count=1,
        )

        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, new_product, form=None, change=False,
            )

        self.assertFalse(
            Product.objects.filter(name='Forced Review Stats Product').exists(),
        )

    def test_save_model_allows_safe_product_edit_and_keeps_review_stats(self):
        before_rating = self.product.rating
        before_count = self.product.reviews_count
        self.product.name = 'Review Stats Guard Product Renamed'
        self.product.description = 'Safe ProductAdmin edit'

        self.admin.save_model(
            self.request, self.product, form=None, change=True,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Review Stats Guard Product Renamed')
        self.assertEqual(self.product.description, 'Safe ProductAdmin edit')
        self.assertEqual(self.product.rating, before_rating)
        self.assertEqual(self.product.reviews_count, before_count)

    def test_crafted_admin_post_cannot_persist_review_aggregates(self):
        """End-to-end: forged POST values are not saved via ProductAdmin."""
        self.client.force_login(self.staff)
        before_rating = self.product.rating
        before_count = self.product.reviews_count

        data = {
            'name': 'Review Stats Posted Product',
            'slug': self.product.slug,
            'description': 'Posted safe description',
            'brand': str(self.brand.pk),
            'primary_category': str(self.category.pk),
            'categories': [str(self.category.pk)],
            'manufacturer_code': 'REVIEW-STATS-MC',
            'status': ProductStatus.ACTIVE,
            'is_featured': 'on',
            'views_count': '0',
            'meta_title': '',
            'meta_description': '',
            # Inline formsets (unchanged).
            'images-TOTAL_FORMS': '0',
            'images-INITIAL_FORMS': '0',
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
            'variants-TOTAL_FORMS': '0',
            'variants-INITIAL_FORMS': '0',
            'variants-MIN_NUM_FORMS': '0',
            'variants-MAX_NUM_FORMS': '1000',
            # Forged payload — must not become a Product writer.
            'rating': '1.00',
            'reviews_count': '99',
        }
        response = self.client.post(
            f'/admin/catalog/product/{self.product.pk}/change/', data,
        )

        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Review Stats Posted Product')
        self.assertEqual(self.product.rating, before_rating)
        self.assertEqual(self.product.reviews_count, before_count)


class ProductReviewAggregateAuthoritativePathStillWorksTests(TestCase):
    """ProductAdmin hardening must not freeze the ReviewService path."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='ReviewStatsPathBrand')
        cls.category = Category.add_root(name='ReviewStatsPathCat')
        cls.product = Product.objects.create(
            name='Review Stats Path Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.user = create_test_user()

    def test_review_service_still_updates_product_review_aggregates(self):
        ReviewService.create_review(
            self.user,
            self.product,
            rating=5,
            text='Отличный товар, рекомендую всем покупателям.',
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('5.00'))
        self.assertEqual(self.product.reviews_count, 1)
