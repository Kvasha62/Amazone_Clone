"""
Фикстуры и утилиты для тестов каталога.

Все тестовые объекты создаются через ORM — без зависимостей от внешних сервисов.
Каждый тестовый класс наследует CatalogTestCase, который создаёт минимальный набор данных.
"""
from decimal import Decimal

from django.test import TestCase, RequestFactory

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Tag,
)


class CatalogTestCase(TestCase):
    """
    Базовый класс для тестов каталога.

    Создаёт:
      - 1 бренд (Samsung)
      - 3 категории в дереве (Электроника → Телефоны → Смартфоны)
      - 1 товар (Galaxy S24)
      - 2 варианта товара
      - 1 тег (флагман)
    """

    @classmethod
    def setUpTestData(cls):
        """Данные, общие для всех тестов в классе."""

        # Бренд
        cls.brand = Brand.objects.create(name='Samsung')

        # Категории (treebeard — через add_root / add_child)
        cls.root_category = Category.add_root(name='Электроника')
        cls.mid_category = cls.root_category.add_child(name='Телефоны')
        cls.leaf_category = cls.mid_category.add_child(name='Смартфоны')

        # Товар
        cls.product = Product.objects.create(
            name='Galaxy S24',
            brand=cls.brand,
            primary_category=cls.leaf_category,
            description='Флагманский смартфон Samsung',
            status=ProductStatus.ACTIVE,
        )
        # M2M
        cls.product.categories.add(cls.leaf_category, cls.mid_category)

        # Варианты
        cls.variant_128 = ProductVariant.objects.create(
            product=cls.product,
            sku='SM-S24-128',
            barcode='8801234567890',
            weight=Decimal('0.168'),
        )
        cls.variant_256 = ProductVariant.objects.create(
            product=cls.product,
            sku='SM-S24-256',
            barcode='8801234567891',
            weight=Decimal('0.171'),
        )

        # Тег
        cls.tag = Tag.objects.create(name='флагман')

    def _make_request(self, method='get', path='/', user=None, data=None):
        """Создаёт тестовый RequestFactory-запрос."""
        factory = RequestFactory()
        request = getattr(factory, method)(path, data=data or {})
        if user:
            request.user = user
        else:
            request.user = type('AnonymousUser', (), {
                'is_authenticated': False,
                'pk': None,
                'is_staff': False,
            })()
        request.session = {}
        return request

    def _create_product(self, **kwargs):
        """Утилита: создаёт товар с дефолтами."""
        defaults = {
            'name': 'Test Product',
            'brand': self.brand,
            'primary_category': self.leaf_category,
            'status': ProductStatus.ACTIVE,
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)
