"""
Тесты QuerySet методов каталога.
"""
from decimal import Decimal

from django.test import TestCase

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    Tag,
)


class ProductQuerySetTests(TestCase):
    """ProductQuerySet — каждая транзакция изолирована."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='Samsung')
        cls.brand_nokia = Brand.objects.create(name='Nokia')
        cls.root_cat = Category.add_root(name='Электроника')
        cls.mid_cat = cls.root_cat.add_child(name='Телефоны')
        cls.leaf_cat = cls.mid_cat.add_child(name='Смартфоны')
        cls.tag = Tag.objects.create(name='флагман-test-qs')

    def setUp(self):
        self.product = Product.objects.create(
            name='Galaxy S24',
            brand=self.brand,
            primary_category=self.leaf_cat,
            status=ProductStatus.ACTIVE,
        )
        self.product.categories.add(self.leaf_cat)

        self.product_draft = Product.objects.create(
            name='Draft Phone',
            brand=self.brand,
            primary_category=self.leaf_cat,
            status=ProductStatus.DRAFT,
        )

        self.product_nokia = Product.objects.create(
            name='Nokia 3310',
            brand=self.brand_nokia,
            primary_category=self.mid_cat,
            status=ProductStatus.ACTIVE,
            min_price=Decimal('50.00'),
            max_price=Decimal('50.00'),
        )

        self.product_expensive = Product.objects.create(
            name='Galaxy Z Fold',
            brand=self.brand,
            primary_category=self.leaf_cat,
            status=ProductStatus.ACTIVE,
            min_price=Decimal('1500.00'),
            max_price=Decimal('2000.00'),
            is_featured=True,
            rating=Decimal('4.80'),
        )
        self.product_expensive.tags.add(self.tag)

    # --- active ---

    def test_active_returns_only_active(self):
        qs = Product.objects.active()
        for p in qs:
            self.assertEqual(p.status, ProductStatus.ACTIVE)

    def test_active_excludes_draft(self):
        qs = Product.objects.active()
        pks = list(qs.values_list('pk', flat=True))
        self.assertNotIn(self.product_draft.pk, pks)

    # --- visible ---

    def test_visible_excludes_draft(self):
        qs = Product.objects.visible()
        pks = list(qs.values_list('pk', flat=True))
        self.assertNotIn(self.product_draft.pk, pks)

    def test_visible_includes_active(self):
        qs = Product.objects.visible()
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product.pk, pks)

    # --- featured ---

    def test_featured_returns_only_featured(self):
        qs = Product.objects.featured()
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_expensive.pk, pks)
        self.assertNotIn(self.product.pk, pks)

    # --- for_category ---

    def test_for_category_m2m(self):
        qs = Product.objects.for_category(self.leaf_cat)
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product.pk, pks)

    # --- for_brand ---

    def test_for_brand(self):
        qs = Product.objects.for_brand(self.brand_nokia)
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_nokia.pk, pks)
        self.assertNotIn(self.product.pk, pks)

    # --- price_range ---

    def test_price_range_min(self):
        qs = Product.objects.active().price_range(min_price=Decimal('1000.00'))
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_expensive.pk, pks)
        self.assertNotIn(self.product_nokia.pk, pks)

    def test_price_range_max(self):
        qs = Product.objects.active().price_range(max_price=Decimal('100.00'))
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_nokia.pk, pks)
        self.assertNotIn(self.product_expensive.pk, pks)

    def test_price_range_both(self):
        qs = Product.objects.active().price_range(
            min_price=Decimal('40.00'),
            max_price=Decimal('60.00'),
        )
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_nokia.pk, pks)

    # --- catalog / for_card ---

    def test_catalog_returns_visible_with_prefetch(self):
        qs = Product.objects.catalog()
        self.assertTrue(qs.exists())

    def test_for_card_returns_with_prefetch(self):
        qs = Product.objects.for_card()
        self.assertTrue(qs.exists())

    # --- composability ---

    def test_composable_filters(self):
        qs = (
            Product.objects
            .active()
            .for_brand(self.brand)
            .price_range(min_price=Decimal('1000.00'))
        )
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_expensive.pk, pks)
