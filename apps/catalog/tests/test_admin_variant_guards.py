"""ARCH-001 Stage 2 — Admin must not bypass PricingService for variants.

Catalog Admin cannot import PricingService (no catalog → pricing).
Therefore ProductVariantAdmin and ProductVariantInline forbid
price-relevant mutations (is_active change, delete, bulk delete).
Legitimate paths remain PricingService.set_variant_active /
delete_variant.
"""
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.catalog.admin.product_admin import ProductVariantInline
from apps.catalog.admin.product_variant_admin import ProductVariantAdmin
from apps.catalog.constants import ProductStatus
from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.pricing.services.pricing_service import PricingService

User = get_user_model()


class ProductVariantAdminGuardTests(TestCase):
    """Admin mutation-path guards for ProductVariant."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='variantadmin',
            email='variantadmin@test.com',
            password='admin123!',
            is_staff=True,
            is_superuser=True,
        )
        cls.brand = Brand.objects.create(name='AdminGuardBrand')
        cls.category = Category.add_root(name='AdminGuardCat')
        cls.product = Product.objects.create(
            name='Admin Guard Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.variant_a = ProductVariant.objects.create(
            product=cls.product,
            sku='AG-A',
            is_active=True,
        )
        cls.variant_b = ProductVariant.objects.create(
            product=cls.product,
            sku='AG-B',
            is_active=True,
        )
        PricingService.set_price(cls.variant_a, Decimal('100.00'))
        PricingService.set_price(cls.variant_b, Decimal('200.00'))
        cls.product.refresh_from_db()

    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductVariantAdmin(ProductVariant, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get('/admin/')
        self.request.user = self.staff

    def test_is_active_is_readonly(self):
        self.assertIn('is_active', self.admin.readonly_fields)

    def test_has_delete_permission_is_false(self):
        self.assertFalse(self.admin.has_delete_permission(self.request))
        self.assertFalse(
            self.admin.has_delete_permission(self.request, obj=self.variant_a),
        )

    def test_delete_model_raises_and_keeps_row_and_bounds(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        with self.assertRaises(PermissionDenied):
            self.admin.delete_model(self.request, self.variant_b)
        self.assertTrue(
            ProductVariant.objects.filter(pk=self.variant_b.pk).exists(),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, before_min)
        self.assertEqual(self.product.max_price, before_max)

    def test_delete_queryset_raises_and_keeps_rows_and_bounds(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        qs = ProductVariant.objects.filter(
            pk__in=[self.variant_a.pk, self.variant_b.pk],
        )
        with self.assertRaises(PermissionDenied):
            self.admin.delete_queryset(self.request, qs)
        self.assertEqual(
            ProductVariant.objects.filter(
                pk__in=[self.variant_a.pk, self.variant_b.pk],
            ).count(),
            2,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, before_min)
        self.assertEqual(self.product.max_price, before_max)

    def test_save_model_rejects_is_active_flip(self):
        before_min = self.product.min_price
        before_max = self.product.max_price
        self.variant_a.is_active = False
        with self.assertRaises(PermissionDenied):
            self.admin.save_model(
                self.request, self.variant_a, form=None, change=True,
            )
        self.variant_a.refresh_from_db()
        self.assertTrue(self.variant_a.is_active)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, before_min)
        self.assertEqual(self.product.max_price, before_max)

    def test_save_model_allows_safe_field_edit(self):
        self.variant_a.weight = Decimal('1.250')
        self.admin.save_model(
            self.request, self.variant_a, form=None, change=True,
        )
        self.variant_a.refresh_from_db()
        self.assertEqual(self.variant_a.weight, Decimal('1.250'))
        self.assertTrue(self.variant_a.is_active)

    def test_inline_is_active_readonly_and_cannot_delete(self):
        inline = ProductVariantInline(Product, self.site)
        self.assertIn('is_active', inline.readonly_fields)
        self.assertFalse(inline.can_delete)


class PricingServiceVariantPathStillWorksTests(TestCase):
    """Legitimate PricingService paths remain the source of truth."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='PSPathBrand')
        cls.category = Category.add_root(name='PSPathCat')
        cls.product = Product.objects.create(
            name='PS Path Product',
            brand=cls.brand,
            primary_category=cls.category,
            status=ProductStatus.ACTIVE,
        )
        cls.variant_a = ProductVariant.objects.create(
            product=cls.product, sku='PS-A', is_active=True,
        )
        cls.variant_b = ProductVariant.objects.create(
            product=cls.product, sku='PS-B', is_active=True,
        )
        PricingService.set_price(cls.variant_a, Decimal('100.00'))
        PricingService.set_price(cls.variant_b, Decimal('200.00'))

    def test_set_variant_active_updates_bounds(self):
        PricingService.set_variant_active(self.variant_b, is_active=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))
        self.assertFalse(
            ProductVariant.objects.get(pk=self.variant_b.pk).is_active,
        )

    def test_delete_variant_updates_bounds(self):
        PricingService.delete_variant(self.variant_b)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))
        self.assertFalse(
            ProductVariant.objects.filter(pk=self.variant_b.pk).exists(),
        )
