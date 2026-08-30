"""Issue #19 — Admin must not bypass PricingService for Product bounds.

``Product.min_price`` / ``Product.max_price`` are denormalized price
bounds. Their single authoritative writer is

    PricingService.recalculate_product_bounds(product)
        → CatalogService.set_product_prices(product, min_price, max_price)

Catalog Admin cannot import PricingService (no ``catalog → pricing``
dependency), so it must not be able to persist modified bounds at all:
the fields are read-only and ``ProductAdmin.save_model`` rejects any
save that would write different bounds (defense-in-depth).

Tests cover:
  1. readonly / form configuration;
  2. server-side rejection of a forced ``save_model`` (change and add);
  3. an end-to-end crafted Admin POST (bounds unchanged, safe fields
     still saved);
  4. the legitimate PricingService / CatalogService path still works.
"""
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.catalog.admin.product_admin import (
    PRODUCT_PRICE_BOUNDS_FIELDS,
    ProductAdmin,
)
from apps.catalog.constants import ProductStatus
from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.pricing.services.pricing_service import PricingService

User = get_user_model()


class ProductAdminPriceBoundsReadOnlyTests(TestCase):
    """min_price / max_price must not be editable in the Admin form."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='boundsadmin',
            email='boundsadmin@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        cls.brand = Brand.objects.create(name='BoundsBrand')
        cls.category = Category.add_root(name='BoundsCat')
        cls.product = Product.objects.create(
            name='Bounds Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku='BOUNDS-A',
            is_active=True,
        )
        PricingService.set_price(cls.variant, Decimal('100.00'))
        cls.product.refresh_from_db()

    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/catalog/product/')
        self.request.user = self.staff

    def test_bounds_are_declared_readonly(self):
        self.assertEqual(
            ('min_price', 'max_price'), PRODUCT_PRICE_BOUNDS_FIELDS,
        )
        for field in PRODUCT_PRICE_BOUNDS_FIELDS:
            self.assertIn(field, self.admin.readonly_fields)

    def test_change_form_has_no_bound_inputs(self):
        """Readonly fields are excluded from the generated ModelForm."""
        form_class = self.admin.get_form(
            self.request, obj=self.product, change=True,
        )
        form_fields = form_class(instance=self.product).fields
        for field in PRODUCT_PRICE_BOUNDS_FIELDS:
            self.assertNotIn(field, form_fields)

    def test_add_form_has_no_bound_inputs(self):
        form_class = self.admin.get_form(self.request, obj=None, change=False)
        form_fields = form_class().fields
        for field in PRODUCT_PRICE_BOUNDS_FIELDS:
            self.assertNotIn(field, form_fields)

    def test_change_page_renders_bounds_as_readonly_text(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            f'/admin/catalog/product/{self.product.pk}/change/',
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Readonly rendering shows the value as text, not as an <input>.
        self.assertIn('100.00', content)
        self.assertNotIn('name="min_price"', content)
        self.assertNotIn('name="max_price"', content)


class ProductAdminPriceBoundsGuardTests(TestCase):
    """Server-side rejection of forced / crafted bound writes."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='guardadmin',
            email='guardadmin@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        cls.brand = Brand.objects.create(name='GuardBrand')
        cls.category = Category.add_root(name='GuardCat')
        cls.product = Product.objects.create(
            name='Guard Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product, sku='GUARD-A', is_active=True,
        )
        PricingService.set_price(cls.variant, Decimal('100.00'))
        cls.product.refresh_from_db()

    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/catalog/product/')
        self.request.user = self.staff

    def _assert_bounds_unchanged(self, min_price, max_price):
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, min_price)
        self.assertEqual(self.product.max_price, max_price)

    def test_save_model_rejects_min_price_change(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        self.product.min_price = Decimal('1.00')
        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, self.product, form=None, change=True,
            )
        self._assert_bounds_unchanged(before_min, before_max)

    def test_save_model_rejects_max_price_change(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        self.product.max_price = Decimal('999999.00')
        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, self.product, form=None, change=True,
            )
        self._assert_bounds_unchanged(before_min, before_max)

    def test_save_model_rejects_clearing_bounds(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        self.product.min_price = None
        self.product.max_price = None
        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, self.product, form=None, change=True,
            )
        self._assert_bounds_unchanged(before_min, before_max)

    def test_save_model_rejects_bounds_on_add(self):
        new_product = Product(
            name='Forced Bounds Product',
            brand=self.brand,
            primary_category=self.category,
            status=ProductStatus.DRAFT,
            min_price=Decimal('1.00'),
            max_price=Decimal('2.00'),
        )
        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, new_product, form=None, change=False,
            )
        self.assertFalse(
            Product.objects.filter(name='Forced Bounds Product').exists(),
        )

    def test_save_model_allows_safe_field_edit(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        self.product.name = 'Guard Product Renamed'
        self.product.description = 'Updated via admin'
        self.admin.save_model(
            self.request, self.product, form=None, change=True,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Guard Product Renamed')
        self.assertEqual(self.product.description, 'Updated via admin')
        self._assert_bounds_unchanged(before_min, before_max)

    def test_save_model_allows_add_without_bounds(self):
        new_product = Product(
            name='Clean Add Product',
            brand=self.brand,
            primary_category=self.category,
            status=ProductStatus.DRAFT,
        )
        self.admin.save_model(
            self.request, new_product, form=None, change=False,
        )
        new_product.refresh_from_db()
        self.assertIsNone(new_product.min_price)
        self.assertIsNone(new_product.max_price)

    def test_crafted_admin_post_cannot_persist_bounds(self):
        """End-to-end: a forged change-form POST must not move bounds."""
        self.client.force_login(self.staff)
        before_min = self.product.min_price
        before_max = self.product.max_price

        data = {
            'name': 'Guard Product Posted',
            'slug': self.product.slug,
            'description': 'Posted description',
            'brand': str(self.brand.pk),
            'primary_category': str(self.category.pk),
            'categories': [str(self.category.pk)],
            'manufacturer_code': 'GUARD-MC',
            'status': ProductStatus.ACTIVE,
            'rating': '0.00',
            'reviews_count': '0',
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
            # Forged payload — must be ignored / rejected.
            'min_price': '1.00',
            'max_price': '2.00',
        }
        response = self.client.post(
            f'/admin/catalog/product/{self.product.pk}/change/', data,
        )
        # The save itself succeeds (safe fields are valid) ...
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Guard Product Posted')
        # ... but the bounds are untouched.
        self.assertEqual(self.product.min_price, before_min)
        self.assertEqual(self.product.max_price, before_max)


class ProductBoundsAuthoritativePathStillWorksTests(TestCase):
    """Read-only Admin must not freeze the authoritative pricing path."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='PathBrand')
        cls.category = Category.add_root(name='PathCat')
        cls.product = Product.objects.create(
            name='Path Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.variant_a = ProductVariant.objects.create(
            product=cls.product, sku='PATH-A', is_active=True,
        )
        cls.variant_b = ProductVariant.objects.create(
            product=cls.product, sku='PATH-B', is_active=True,
        )
        PricingService.set_price(cls.variant_a, Decimal('100.00'))
        PricingService.set_price(cls.variant_b, Decimal('200.00'))

    def test_set_price_still_updates_bounds(self):
        PricingService.set_price(self.variant_a, Decimal('50.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('50.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_recalculate_bounds_still_updates_bounds(self):
        PricingService.set_variant_active(self.variant_b, is_active=False)
        PricingService.recalculate_product_bounds(self.product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))
