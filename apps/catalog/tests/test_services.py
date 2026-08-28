"""
Тесты CatalogService — бизнес-логика каталога.
"""
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    Tag,
)
from apps.catalog.services.catalog_service import (
    CatalogService,
    notify_price_relevant_state_changed,
    register_price_bounds_listener,
)
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


class ProductPriceUpdatingTests(CatalogTestCase):
    """
    Тесты CatalogService.set_product_prices().

    Это ЕДИНСТВЕННАЯ точка mutation денормализованных цен в каталоге.
    Метод принимает УЖЕ РАССЧИТАННЫЕ min_price/max_price и только
    записывает их в catalog.Product (ARCH-001: Pricing → Catalog ownership).
    """

    def test_set_product_prices_updates_min_max(self):
        """Готовые min/max записываются на Product."""
        CatalogService.set_product_prices(
            self.product,
            min_price=Decimal('100.00'),
            max_price=Decimal('200.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_set_product_prices_accepts_none(self):
        """Нет цен → передаются None → поля обнуляются."""
        CatalogService.set_product_prices(
            self.product,
            min_price=None,
            max_price=None,
        )
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)

    def test_set_product_prices_single_price(self):
        """Одна цена → min = max."""
        CatalogService.set_product_prices(
            self.product,
            min_price=Decimal('150.00'),
            max_price=Decimal('150.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('150.00'))
        self.assertEqual(self.product.max_price, Decimal('150.00'))

    def test_set_product_prices_only_mutates_price_fields(self):
        """Метод не трогает прочие поля товара (name, status...)."""
        original_name = self.product.name
        original_status = self.product.status
        CatalogService.set_product_prices(
            self.product,
            min_price=Decimal('50.00'),
            max_price=Decimal('50.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, original_name)
        self.assertEqual(self.product.status, original_status)


class CatalogNoPricingDependencyTests(TestCase):
    """
    ARCH-001 regression: в каталоге НЕТ обратной зависимости catalog → pricing.

    Контракт обновления цен (CatalogService.set_product_prices) должен
    принимать готовые значения и НЕ импортировать/не читать цены из
    bounded context pricing. Тест НЕ использует mock, который скрывает
    настоящий импорт: он анализирует исходный код контракта и модуля.
    """

    @staticmethod
    def _imported_modules(source):
        """Собирает имена модулей, импортируемых в исходнике."""
        import ast
        tree = ast.parse(source)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.append(node.module)
        return modules

    def test_catalog_service_module_does_not_import_pricing(self):
        """Модуль apps.catalog.services.catalog_service не импортирует pricing."""
        import inspect
        module_file = inspect.getfile(CatalogService)
        with open(module_file, encoding='utf-8') as fh:
            source = fh.read()
        modules = self._imported_modules(source)
        self.assertNotIn(
            'apps.pricing',
            modules,
            'catalog_service не должен импортировать apps.pricing '
            '(обратная зависимость catalog → pricing).',
        )
        self.assertFalse(
            any(m.startswith('apps.pricing') for m in modules),
            'catalog_service не должен импортировать любой модуль pricing.',
        )

    def test_set_product_prices_does_not_read_prices(self):
        """
        CatalogService.set_product_prices() не читает цены из pricing.

        Метод принимает рассчитанные min_price/max_price и записывает их.
        В нём не должно быть обращения к `price__price` (чтение таблицы цен),
        к модели Price и к импорту apps.pricing — это и есть обратная
        зависимость catalog → pricing, которую убирает ARCH-001.
        """
        import inspect
        source = inspect.getsource(CatalogService.set_product_prices)
        self.assertNotIn('price__price', source)
        self.assertNotIn('Price', source)
        self.assertNotIn('apps.pricing', source)
        # Контракт должен записывать только поля catalog.Product.
        self.assertIn('product.min_price', source)
        self.assertIn('product.max_price', source)
        self.assertIn('product.save', source)

    # ── ARCH-001 Stage 2: всё production-дерево каталога ──

    # Production-код каталога. management/commands (populate_*) — dev-тулинг:
    # он легитимно создаёт pricing-фикстуры при сеянии и исключён
    # из проверки (как и tests/).
    PRODUCTION_SUBPATHS = (
        'apps/catalog/apps.py',
        'apps/catalog/constants.py',
        'apps/catalog/urls.py',
        'apps/catalog/signals.py',
        'apps/catalog/admin',
        'apps/catalog/api_views',
        'apps/catalog/managers',
        'apps/catalog/models',
        'apps/catalog/querysets',
        'apps/catalog/serializers',
        'apps/catalog/services',
    )

    def _production_sources(self):
        """Исходники production-кода каталога: (path, source)."""
        repo_root = Path(__file__).resolve().parents[3]
        for sub in self.PRODUCTION_SUBPATHS:
            path = repo_root / sub
            if path.is_file():
                yield path, path.read_text(encoding='utf-8')
            elif path.is_dir():
                for py_file in sorted(path.rglob('*.py')):
                    yield py_file, py_file.read_text(encoding='utf-8')

    def test_production_catalog_does_not_import_pricing(self):
        """
        Ни один production-модуль catalog не импортирует apps.pricing.

        ARCH-001 Stage 2: единственное направление зависимости —
        pricing → catalog. Каталог общается с pricing только через
        контракт слушателей (динамический колбэк, без импорта).
        """
        for path, source in self._production_sources():
            modules = self._imported_modules(source)
            bad = [
                m for m in modules
                if m == 'apps.pricing' or m.startswith('apps.pricing.')
            ]
            self.assertEqual(
                bad, [],
                f'{path} импортирует pricing — запрещённая обратная '
                f'зависимость catalog → pricing: {bad}',
            )

    def test_production_catalog_has_no_price_price_lookup(self):
        """
        Нигде в production-каталоге нет ORM-lookup `price__price`
        (чтение таблицы цен pricing через JOIN из каталога).
        """
        for path, source in self._production_sources():
            self.assertNotIn(
                'price__price', source,
                f'{path} читает цены через price__price — обратная '
                f'зависимость catalog → pricing',
            )

    def test_product_model_has_no_recalculate_prices(self):
        """
        Product.recalculate_prices() удалён (ARCH-001 Stage 2):
        модель каталога больше не умеет читать цены pricing.
        """
        self.assertFalse(
            hasattr(Product, 'recalculate_prices'),
            'Product.recalculate_prices должен быть удалён — '
            'расчёт границ теперь в pricing, запись в CatalogService.',
        )


class PriceBoundsListenerContractTests(CatalogTestCase):
    """
    ARCH-001 Stage 2: контракт price-relevant событий каталога.

    catalog уведомляет зарегистрированных слушателей без Django-сигналов
    и без импорта pricing. Слушателя регистрирует pricing в ready()
    (проверка wiring — в apps/pricing/tests).
    """

    def test_notify_calls_registered_listener_with_product(self):
        """notify() синхронно вызывает слушателя с товаром-аргументом."""
        from apps.catalog.services import catalog_service
        listener = mock.Mock()
        with mock.patch.object(
            catalog_service, '_price_bounds_listeners', [],
        ) as registry:
            registry.append(listener)
            notify_price_relevant_state_changed(self.product)
        listener.assert_called_once_with(self.product)

    def test_notify_calls_each_listener_once(self):
        """Несколько слушателей вызываются все, по одному разу."""
        from apps.catalog.services import catalog_service
        first, second = mock.Mock(), mock.Mock()
        with mock.patch.object(
            catalog_service, '_price_bounds_listeners', [],
        ) as registry:
            registry.append(first)
            registry.append(second)
            notify_price_relevant_state_changed(self.product)
        first.assert_called_once_with(self.product)
        second.assert_called_once_with(self.product)

    def test_notify_without_listeners_is_noop(self):
        """Нет слушателей → безопасный no-op (без исключений)."""
        from apps.catalog.services import catalog_service
        with mock.patch.object(
            catalog_service, '_price_bounds_listeners', [],
        ):
            notify_price_relevant_state_changed(self.product)

    def test_register_ignores_duplicate_listener(self):
        """Повторная регистрация того же слушателя не дублирует его."""
        from apps.catalog.services import catalog_service

        def fake_listener(product):
            pass

        with mock.patch.object(
            catalog_service, '_price_bounds_listeners', [],
        ) as registry:
            register_price_bounds_listener(fake_listener)
            register_price_bounds_listener(fake_listener)
            self.assertEqual(list(registry), [fake_listener])


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
