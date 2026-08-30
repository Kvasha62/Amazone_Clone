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
import threading
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection, connections, transaction
from django.db.models import Avg, Count
from django.test import (
    RequestFactory,
    TestCase,
    TransactionTestCase,
    skipUnlessDBFeature,
)
from django.test.utils import CaptureQueriesContext

from apps.catalog.admin.product_admin import (
    PRODUCT_ADMIN_PROTECTED_FIELDS,
    PRODUCT_REVIEW_AGGREGATE_FIELDS,
    ProductAdmin,
)
from apps.catalog.constants import ProductStatus
from apps.catalog.models import Brand, Category, Product
from apps.catalog.services.catalog_service import CatalogService
from apps.orders.tests.factories import create_test_user
from apps.reviews.models import Review
from apps.reviews.services.review_service import ReviewService

User = get_user_model()


def expected_review_aggregate(product):
    """Independent approved-review aggregate used by H2 regression tests."""
    approved = product.reviews.filter(is_approved=True)
    total = approved.aggregate(total=Count('id'))['total'] or 0
    avg_raw = approved.aggregate(avg=Avg('rating'))['avg']
    avg = round(Decimal(str(avg_raw or Decimal('0.00'))), 2)
    return avg, total


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

    def test_save_model_update_sql_excludes_protected_aggregate_fields(self):
        """ProductAdmin change-save must not full-save derived fields."""
        self.product.name = 'Review Stats SQL Product Renamed'
        self.product.description = 'SQL field-set check'

        with CaptureQueriesContext(connection) as captured:
            self.admin.save_model(
                self.request, self.product, form=None, change=True,
            )

        product_updates = [
            query['sql']
            for query in captured.captured_queries
            if 'UPDATE "catalog_product"' in query['sql']
        ]
        self.assertTrue(product_updates)
        update_sql = '\n'.join(product_updates)

        self.assertIn('"name"', update_sql)
        self.assertIn('"description"', update_sql)
        self.assertIn('"updated_at"', update_sql)
        for field in PRODUCT_ADMIN_PROTECTED_FIELDS:
            self.assertNotIn(f'"{field}"', update_sql)

    def test_save_model_status_activation_still_sets_published_at(self):
        """update_fields must preserve Product.save() managed fields."""
        draft = Product.objects.create(
            name='Review Stats Draft Product',
            brand=self.brand,
            primary_category=self.category,
            status=ProductStatus.DRAFT,
        )
        self.assertIsNone(draft.published_at)

        draft.status = ProductStatus.ACTIVE
        self.admin.save_model(self.request, draft, form=None, change=True)

        draft.refresh_from_db()
        self.assertEqual(draft.status, ProductStatus.ACTIVE)
        self.assertIsNotNone(draft.published_at)

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
        with CaptureQueriesContext(connection) as captured:
            response = self.client.post(
                f'/admin/catalog/product/{self.product.pk}/change/', data,
            )

        self.assertEqual(response.status_code, 302)
        product_updates = [
            query['sql']
            for query in captured.captured_queries
            if 'UPDATE "catalog_product"' in query['sql']
        ]
        self.assertTrue(product_updates)
        update_sql = '\n'.join(product_updates)
        self.assertIn('"name"', update_sql)
        self.assertIn('"updated_at"', update_sql)
        for field in PRODUCT_ADMIN_PROTECTED_FIELDS:
            self.assertNotIn(f'"{field}"', update_sql)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Review Stats Posted Product')
        self.assertEqual(self.product.rating, before_rating)
        self.assertEqual(self.product.reviews_count, before_count)


@skipUnlessDBFeature('has_select_for_update')
class ProductAdminReviewAggregateConcurrencyTests(TransactionTestCase):
    """Regression: stale ProductAdmin instances must not overwrite aggregates."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.factory = RequestFactory()
        self.staff = User.objects.create_user(
            username='reviewstatsconcurrency',
            email='reviewstatsconcurrency@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        self.request = self.factory.post('/admin/catalog/product/')
        self.request.user = self.staff
        self.brand = Brand.objects.create(name='ReviewStatsConcurrencyBrand')
        self.category = Category.add_root(name='ReviewStatsConcurrencyCat')
        self.product = Product.objects.create(
            name='Review Stats Concurrency Product',
            brand=self.brand,
            primary_category=self.category,
            status=ProductStatus.ACTIVE,
        )
        self.review_user = create_test_user(
            email='reviewstatsconcurrency-author@test.com',
        )
        self.review = ReviewService.create_review(
            self.review_user,
            self.product,
            rating=4,
            text='Достаточно подробный отзыв для проверки конкурентности.',
        )

    def test_stale_product_admin_save_does_not_overwrite_review_stats(self):
        """T1 Admin safe edit must exclude stale rating/reviews_count from UPDATE."""
        admin_product = Product.objects.get(pk=self.product.pk)
        admin_product.name = 'Review Stats Concurrency Product Renamed'
        product_id = self.product.pk
        review_id = self.review.pk
        admin_name = admin_product.name
        save_started = threading.Event()
        service_committed = threading.Event()
        original_save = Product.save
        admin_save_kwargs = {}
        errors = []

        def patched_save(instance, *args, **kwargs):
            if (
                instance.pk == product_id
                and instance.name == admin_name
                and not save_started.is_set()
            ):
                admin_save_kwargs.update(kwargs)
                save_started.set()
                if not service_committed.wait(timeout=10):
                    raise RuntimeError('ReviewService update did not commit')
            return original_save(instance, *args, **kwargs)

        def admin_safe_edit():
            connections.close_all()
            try:
                with transaction.atomic():
                    self.admin.save_model(
                        self.request,
                        admin_product,
                        form=None,
                        change=True,
                    )
            except Exception as exc:  # noqa: BLE001 - asserted below.
                errors.append(exc)
            finally:
                connections.close_all()

        Product.save = patched_save
        try:
            admin_thread = threading.Thread(target=admin_safe_edit)
            admin_thread.start()

            self.assertTrue(
                save_started.wait(timeout=10),
                'ProductAdmin did not reach Product.save()',
            )

            connections.close_all()
            service_review = ReviewService.update_review(
                Review.objects.select_related('product', 'user').get(pk=review_id),
                user=self.review_user,
                rating=5,
            )
            self.assertEqual(service_review.rating, 5)

            after_service = Product.objects.get(pk=product_id)
            self.assertEqual(after_service.rating, Decimal('5.00'))
            self.assertEqual(after_service.reviews_count, 1)

            service_committed.set()
            admin_thread.join(timeout=10)
            self.assertFalse(admin_thread.is_alive())
        finally:
            Product.save = original_save
            connections.close_all()

        self.assertEqual(errors, [])
        update_fields = set(admin_save_kwargs['update_fields'])
        for field in PRODUCT_ADMIN_PROTECTED_FIELDS:
            self.assertNotIn(field, update_fields)

        final_product = Product.objects.get(pk=product_id)
        expected_rating, expected_count = expected_review_aggregate(final_product)
        self.assertEqual(final_product.name, admin_name)
        self.assertEqual(final_product.rating, expected_rating)
        self.assertEqual(final_product.reviews_count, expected_count)
        self.assertEqual(final_product.rating, Decimal('5.00'))
        self.assertEqual(final_product.reviews_count, 1)


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
