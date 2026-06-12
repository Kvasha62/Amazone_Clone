"""
Фикстуры и утилиты для тестов ценообразования.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.catalog.constants import ProductStatus
from apps.pricing.models import Price

User = get_user_model()


class PricingTestCase(TestCase):
    """
    Базовый класс для тестов ценообразования.

    Создаёт:
      - 1 staff-пользователь (staff)
      - 1 бренд, 1 категория, 1 товар
      - 2 варианта (SKU-P1, SKU-P2) — без цен
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='pricestaff',
            email='pricestaff@test.com',
            password='staff123!',
            is_staff=True,
        )
        cls.brand = Brand.objects.create(name='PriceTestBrand')
        cls.root_cat = Category.add_root(name='ЦеныКаталог')
        cls.product = Product.objects.create(
            name='Price Test Product',
            brand=cls.brand,
            primary_category=cls.root_cat,
            status=ProductStatus.ACTIVE,
        )
        cls.variant_a = ProductVariant.objects.create(
            product=cls.product,
            sku='SKU-P1',
            is_active=True,
        )
        cls.variant_b = ProductVariant.objects.create(
            product=cls.product,
            sku='SKU-P2',
            is_active=True,
        )
        cls.variant_inactive = ProductVariant.objects.create(
            product=cls.product,
            sku='SKU-P-INACTIVE',
            is_active=False,
        )

    def _set_price(self, variant, price, sale_price=None):
        """Быстрая установка цены через сервис."""
        from apps.pricing.services.pricing_service import PricingService
        return PricingService.set_price(
            variant=variant,
            price=Decimal(str(price)),
            sale_price=Decimal(str(sale_price)) if sale_price is not None else None,
        )
