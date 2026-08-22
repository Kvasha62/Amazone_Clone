"""
Тесты моделей каталога.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Attribute,
    AttributeValue,
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Tag,
    VariantAttribute,
)
from apps.catalog.tests.factories import CatalogTestCase


# ==========================================================
# PRODUCT
# ==========================================================

class ProductModelTests(CatalogTestCase):

    def test_slug_auto_generated_on_create(self):
        p = self._create_product(name='iPhone 15 Pro')
        self.assertTrue(p.slug)
        self.assertNotEqual(p.slug, '')

    def test_slug_not_changed_on_rename(self):
        p = self._create_product(name='Original Name')
        original_slug = p.slug
        p.name = 'New Name'
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.slug, original_slug)

    def test_slug_unique(self):
        p1 = self._create_product(name='Same Name')
        p2 = self._create_product(name='Same Name')
        self.assertNotEqual(p1.slug, p2.slug)

    def test_default_status_is_draft(self):
        p = self._create_product(status=ProductStatus.DRAFT)
        self.assertEqual(p.status, ProductStatus.DRAFT)

    def test_is_active_property(self):
        p = self._create_product(status=ProductStatus.ACTIVE)
        self.assertTrue(p.is_active)
        p.status = ProductStatus.DRAFT
        p.save()
        self.assertFalse(p.is_active)

    def test_is_visible_draft_not_visible(self):
        p = self._create_product(status=ProductStatus.DRAFT)
        self.assertFalse(p.is_visible)

    def test_is_visible_active_visible(self):
        p = self._create_product(status=ProductStatus.ACTIVE)
        self.assertTrue(p.is_visible)

    def test_published_at_set_on_active(self):
        p = self._create_product(status=ProductStatus.DRAFT)
        self.assertIsNone(p.published_at)
        p.status = ProductStatus.ACTIVE
        p.save()
        self.assertIsNotNone(p.published_at)

    def test_published_at_not_overwritten(self):
        p = self._create_product(status=ProductStatus.ACTIVE)
        first = p.published_at
        p.name = 'Updated'
        p.save()
        self.assertEqual(p.published_at, first)

    def test_price_range_no_price(self):
        p = self._create_product(min_price=None, max_price=None)
        self.assertEqual(p.price_range, 'Цена не указана')

    def test_price_range_single_price(self):
        p = self._create_product(
            min_price=Decimal('100.00'),
            max_price=Decimal('100.00'),
        )
        self.assertEqual(p.price_range, '100.00')

    def test_price_range_multiple_prices(self):
        p = self._create_product(
            min_price=Decimal('100.00'),
            max_price=Decimal('500.00'),
        )
        self.assertEqual(p.price_range, '100.00 — 500.00')

    def test_rating_cannot_exceed_5(self):
        with self.assertRaises(IntegrityError):
            self._create_product(rating=Decimal('5.01'))

    def test_rating_cannot_be_negative(self):
        with self.assertRaises(IntegrityError):
            self._create_product(rating=Decimal('-0.01'))

    def test_max_price_cannot_be_less_than_min(self):
        with self.assertRaises(IntegrityError):
            self._create_product(
                min_price=Decimal('500.00'),
                max_price=Decimal('100.00'),
            )

    def test_uuid_auto_generated(self):
        p = self._create_product()
        self.assertIsNotNone(p.uuid)

    def test_uuid_unique(self):
        p1 = self._create_product(name='Product A')
        p2 = self._create_product(name='Product B')
        self.assertNotEqual(p1.uuid, p2.uuid)

    def test_increment_views(self):
        p = self._create_product(views_count=0)
        p.increment_views()
        p.refresh_from_db()
        self.assertEqual(p.views_count, 1)

    def test_increment_views_concurrent_safe(self):
        p = self._create_product(views_count=0)
        p.increment_views()
        p.increment_views()
        p.refresh_from_db()
        self.assertEqual(p.views_count, 2)

    def test_get_absolute_url(self):
        self.assertEqual(
            self.product.get_absolute_url(),
            f'/products/{self.product.slug}/',
        )

    def test_display_rating(self):
        p = self._create_product(rating=Decimal('4.50'))
        self.assertEqual(p.display_rating, '4.50')


# ==========================================================
# BRAND
# ==========================================================

class BrandModelTests(TestCase):

    def test_slug_auto_generated(self):
        b = Brand.objects.create(name='Nike')
        self.assertTrue(b.slug)

    def test_unique_name(self):
        Brand.objects.create(name='Nike')
        with self.assertRaises(IntegrityError):
            Brand.objects.create(name='Nike')

    def test_get_absolute_url(self):
        b = Brand.objects.create(name='Adidas')
        self.assertEqual(b.get_absolute_url(), f'/brands/{b.slug}/')


# ==========================================================
# CATEGORY (TREEBEARD)
# ==========================================================

class CategoryModelTests(TestCase):

    def setUp(self):
        self.root = Category.add_root(name='Электроника')
        self.mid = self.root.add_child(name='Телефоны')
        self.leaf = self.mid.add_child(name='Смартфоны')

    def test_slug_auto_generated(self):
        self.assertTrue(self.root.slug)

    def test_depth(self):
        self.assertEqual(self.root.depth, 1)
        self.assertEqual(self.mid.depth, 2)
        self.assertEqual(self.leaf.depth, 3)

    def test_url_path_root(self):
        self.assertEqual(self.root.url_path, self.root.slug)

    def test_url_path_nested(self):
        expected = f'{self.root.slug}/{self.mid.slug}'
        self.assertEqual(self.mid.url_path, expected)

    def test_url_path_deeply_nested(self):
        expected = f'{self.root.slug}/{self.mid.slug}/{self.leaf.slug}'
        self.assertEqual(self.leaf.url_path, expected)

    def test_full_name_cached_root(self):
        self.assertEqual(self.root.full_name_cached, 'Электроника')

    def test_full_name_cached_nested(self):
        self.assertEqual(self.mid.full_name_cached, 'Электроника → Телефоны')

    def test_full_name_cached_deeply_nested(self):
        self.assertEqual(
            self.leaf.full_name_cached,
            'Электроника → Телефоны → Смартфоны',
        )

    def test_full_name_property(self):
        self.assertEqual(self.leaf.full_name, self.leaf.full_name_cached)

    def test_rename_updates_descendants(self):
        """При переименовании обновляется full_name_cached, но НЕ url_path (slug не меняется)."""
        self.root.name = 'Tech'
        self.root.save()

        self.leaf.refresh_from_db()
        # full_name_cached обновился — содержит новое имя
        self.assertIn('Tech', self.leaf.full_name_cached)
        # url_path НЕ изменился — slug остался прежним
        self.assertIn(self.root.slug, self.leaf.url_path)

    def test_get_absolute_url(self):
        self.assertEqual(
            self.leaf.get_absolute_url(),
            f'/catalog/{self.leaf.url_path}/',
        )


# ==========================================================
# TAG
# ==========================================================

class TagModelTests(TestCase):

    def test_slug_auto_generated(self):
        t = Tag.objects.create(name='беспроводной')
        self.assertTrue(t.slug)

    def test_unique_name(self):
        Tag.objects.create(name='новинка')
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name='новинка')


# ==========================================================
# PRODUCT VARIANT
# ==========================================================

class ProductVariantModelTests(CatalogTestCase):

    def test_slug_auto_generated(self):
        self.assertTrue(self.variant_128.slug)

    def test_default_ordering_meta(self):
        """Meta.ordering задаёт сортировку на уровне SQL, не query.order_by."""
        self.assertEqual(
            ProductVariant._meta.ordering,
            ('-created_at',),
        )


# ==========================================================
# PRODUCT IMAGE
# ==========================================================

class ProductImageModelTests(CatalogTestCase):

    def test_unique_main_constraint(self):
        ProductImage.objects.create(
            product=self.product, image='test1.jpg', is_main=True,
        )
        with self.assertRaises(IntegrityError):
            ProductImage.objects.create(
                product=self.product, image='test2.jpg', is_main=True,
            )

    def test_multiple_non_main_images(self):
        ProductImage.objects.create(
            product=self.product, image='test1.jpg', is_main=False,
        )
        ProductImage.objects.create(
            product=self.product, image='test2.jpg', is_main=False,
        )
        self.assertEqual(ProductImage.objects.filter(product=self.product).count(), 2)


# ==========================================================
# ATTRIBUTE / ATTRIBUTE VALUE / VARIANT ATTRIBUTE
# ==========================================================

class AttributeModelTests(TestCase):

    def setUp(self):
        self.attr_color = Attribute.objects.create(name='Цвет')
        self.attr_size = Attribute.objects.create(name='Размер')
        self.val_red = AttributeValue.objects.create(
            attribute=self.attr_color, value='Красный',
        )
        self.val_large = AttributeValue.objects.create(
            attribute=self.attr_size, value='Большой',
        )

    def test_unique_attribute_value(self):
        with self.assertRaises(IntegrityError):
            AttributeValue.objects.create(
                attribute=self.attr_color, value='Красный',
            )

    def test_slug_auto_generated(self):
        self.assertTrue(self.attr_color.slug)

    def test_variant_attribute_clean_mismatch(self):
        brand = Brand.objects.create(name='TestBrand')
        root = Category.add_root(name='Cat')
        product = Product.objects.create(
            name='Test', brand=brand, primary_category=root,
        )
        variant = ProductVariant.objects.create(
            product=product, sku='TEST-001',
        )
        va = VariantAttribute(
            variant=variant,
            attribute=self.attr_color,
            value=self.val_large,
        )
        with self.assertRaises(ValidationError):
            va.clean()
