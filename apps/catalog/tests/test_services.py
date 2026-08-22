"""
Тесты CatalogService — бизнес-логика каталога.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    Tag,
)
from apps.catalog.services.catalog_service import CatalogService
from apps.catalog.tests.factories import CatalogTestCase


class ProductRetrievalTests(CatalogTestCase):

    def test_get_by_uuid(self):
        product = CatalogService.get_product_by_uuid(str(self.product.uuid))
        self.assertEqual(product.pk, self.product.pk)

    def test_get_by_uuid_not_found(self):
        with self.assertRaises(NotFound):
            CatalogService.get_product_by_uuid('00000000-0000-0000-0000-000000000000')

    def test_get_by_uuid_draft_not_found(self):
        draft = self._create_product(status=ProductStatus.DRAFT)
        with self.assertRaises(NotFound):
            CatalogService.get_product_by_uuid(str(draft.uuid))

    def test_get_by_slug(self):
        product = CatalogService.get_product_by_slug(self.product.slug)
        self.assertEqual(product.pk, self.product.pk)

    def test_get_by_slug_not_found(self):
        with self.assertRaises(NotFound):
            CatalogService.get_product_by_slug('nonexistent-slug')


class ProductListingTests(CatalogTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.brand_nokia = Brand.objects.create(name='Nokia')
        cls.product_nokia = Product.objects.create(
            name='Nokia 3310',
            brand=cls.brand_nokia,
            primary_category=cls.mid_category,
            status=ProductStatus.ACTIVE,
            min_price=Decimal('50.00'),
            max_price=Decimal('50.00'),
        )

    def test_listing_basic(self):
        qs, filters = CatalogService.get_product_listing()
        self.assertTrue(qs.exists())
        self.assertEqual(filters, {})

    def test_listing_filter_by_category(self):
        qs, filters = CatalogService.get_product_listing(
            category_slug=self.leaf_category.slug,
        )
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product.pk, pks)
        self.assertIn('category', filters)

    def test_listing_filter_by_brand(self):
        qs, filters = CatalogService.get_product_listing(
            brand_slug=self.brand.slug,
        )
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product.pk, pks)
        self.assertNotIn(self.product_nokia.pk, pks)

    def test_listing_filter_by_price(self):
        qs, filters = CatalogService.get_product_listing(
            min_price=Decimal('40.00'),
            max_price=Decimal('60.00'),
        )
        pks = list(qs.values_list('pk', flat=True))
        self.assertIn(self.product_nokia.pk, pks)

    def test_listing_ordering_whitelist(self):
        qs, _ = CatalogService.get_product_listing(ordering='DROP TABLE products')
        self.assertTrue(qs.exists())

    def test_listing_ordering_by_price_asc(self):
        qs, _ = CatalogService.get_product_listing(ordering='min_price')
        products = list(qs)
        if len(products) >= 2:
            # Фильтруем товары БЕЗ цены (min_price=None) —
            # их порядок зависит от БД (PostgreSQL: NULLS LAST, SQLite: NULLS FIRST).
            # Проверяем сортировку только для товаров С ценой.
            priced = [p for p in products if p.min_price is not None]
            if len(priced) >= 2:
                self.assertLessEqual(
                    priced[0].min_price,
                    priced[1].min_price,
                )


class ProductCreateTests(CatalogTestCase):

    def test_create_basic(self):
        product = CatalogService.create_product(
            name='New Phone',
            brand_id=self.brand.pk,
            primary_category_id=self.leaf_category.pk,
        )
        self.assertEqual(product.name, 'New Phone')
        self.assertEqual(product.brand_id, self.brand.pk)
        self.assertEqual(product.status, ProductStatus.DRAFT)
        self.assertTrue(product.slug)

    def test_create_with_categories_and_tags(self):
        tag = Tag.objects.create(name='новинка-test')
        product = CatalogService.create_product(
            name='Tagged Phone',
            brand_id=self.brand.pk,
            primary_category_id=self.leaf_category.pk,
            category_ids=[self.leaf_category.pk, self.mid_category.pk],
            tag_ids=[tag.pk],
        )
        self.assertEqual(product.categories.count(), 2)
        self.assertEqual(product.tags.count(), 1)

    def test_create_invalid_brand(self):
        with self.assertRaises(ValidationError) as ctx:
            CatalogService.create_product(
                name='Test',
                brand_id=99999,
                primary_category_id=self.leaf_category.pk,
            )
        self.assertIn('brand', ctx.exception.detail)

    def test_create_invalid_category(self):
        with self.assertRaises(ValidationError) as ctx:
            CatalogService.create_product(
                name='Test',
                brand_id=self.brand.pk,
                primary_category_id=99999,
            )
        self.assertIn('primary_category', ctx.exception.detail)


class ProductUpdateTests(CatalogTestCase):

    def test_update_name(self):
        product = CatalogService.update_product(
            self.product,
            name='Galaxy S24 Ultra',
        )
        self.assertEqual(product.name, 'Galaxy S24 Ultra')

    def test_update_status_to_active(self):
        draft = self._create_product(status=ProductStatus.DRAFT)
        product = CatalogService.update_product(draft, status=ProductStatus.ACTIVE)
        self.assertEqual(product.status, ProductStatus.ACTIVE)
        self.assertIsNotNone(product.published_at)

    def test_update_categories(self):
        CatalogService.update_product(
            self.product,
            category_ids=[self.leaf_category.pk],
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.categories.count(), 1)

    def test_update_nonexistent_brand(self):
        with self.assertRaises(ValidationError) as ctx:
            CatalogService.update_product(self.product, brand_id=99999)
        self.assertIn('brand', ctx.exception.detail)

    def test_update_nothing_changes(self):
        product = CatalogService.update_product(self.product)
        self.assertEqual(product.pk, self.product.pk)


class ProductViewsIncrementTests(CatalogTestCase):

    def test_increment(self):
        CatalogService.increment_product_views(self.product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.views_count, 1)


class CategoryServiceTests(TestCase):

    def setUp(self):
        self.root = Category.add_root(name='Электроника')
        self.mid = self.root.add_child(name='Телефоны')
        self.leaf = self.mid.add_child(name='Смартфоны')

    def test_get_category_tree(self):
        roots = CatalogService.get_category_tree()
        self.assertTrue(len(roots) > 0)

    def test_get_category_by_slug(self):
        cat = CatalogService.get_category_by_slug(self.root.slug)
        self.assertEqual(cat.pk, self.root.pk)

    def test_get_category_by_slug_not_found(self):
        with self.assertRaises(NotFound):
            CatalogService.get_category_by_slug('nonexistent')

    def test_get_category_breadcrumbs(self):
        breadcrumbs = CatalogService.get_category_breadcrumbs(self.leaf)
        names = [b['name'] for b in breadcrumbs]
        self.assertEqual(names, ['Электроника', 'Телефоны', 'Смартфоны'])

    def test_breadcrumbs_root(self):
        breadcrumbs = CatalogService.get_category_breadcrumbs(self.root)
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(breadcrumbs[0]['name'], 'Электроника')


class BrandServiceTests(TestCase):

    def setUp(self):
        self.brand = Brand.objects.create(name='Nike')
        Brand.objects.create(name='Inactive', is_active=False)

    def test_get_active_brands(self):
        brands = CatalogService.get_active_brands()
        names = list(brands.values_list('name', flat=True))
        self.assertIn('Nike', names)
        self.assertNotIn('Inactive', names)

    def test_get_brand_by_slug(self):
        brand = CatalogService.get_brand_by_slug(self.brand.slug)
        self.assertEqual(brand.pk, self.brand.pk)

    def test_get_brand_by_slug_not_found(self):
        with self.assertRaises(NotFound):
            CatalogService.get_brand_by_slug('nonexistent')


class TagServiceTests(TestCase):

    def setUp(self):
        self.tag = Tag.objects.create(name='новинка-test')
        Tag.objects.create(name='скрытый-test', is_active=False)

    def test_get_active_tags(self):
        tags = CatalogService.get_active_tags()
        names = list(tags.values_list('name', flat=True))
        self.assertIn('новинка-test', names)
        self.assertNotIn('скрытый-test', names)
