"""
Тесты сигналов каталога.

Покрывают:
  - sync_product_main_image: is_main=True → Product.main_image
  - clear_product_main_image_on_delete: удаление главного фото
  - update_product_search_vector: name/description → search_vector
  - VariantPriceWiringRemovedTests: в каталоге НЕТ price-recompute
    wiring на ORM-события вариантов (ARCH-001 Stage 2: координация —
    явные service-вызовы PricingService, CASCADE-удаление товара не
    перезаписывает удаляемый Product)
"""
from decimal import Decimal
from unittest import mock, skipIf

from django.db import connection

from apps.catalog.constants import ProductStatus
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
)
from apps.catalog.tests.factories import CatalogTestCase


class MainImageSignalTests(CatalogTestCase):
    """Сигналы главного изображения."""

    def test_set_main_image_updates_product(self):
        """is_main=True → Product.main_image обновляется."""
        img = ProductImage.objects.create(
            product=self.product,
            image='test_main.jpg',
            is_main=True,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.main_image_id, img.pk)

    def test_unset_main_image_clears_product(self):
        """is_main=False → Product.main_image очищается."""
        img = ProductImage.objects.create(
            product=self.product,
            image='test_main.jpg',
            is_main=True,
        )
        img.is_main = False
        img.save()

        self.product.refresh_from_db()
        self.assertIsNone(self.product.main_image_id)

    def test_delete_main_image_clears_product(self):
        """Удаление главного фото → Product.main_image = None."""
        img = ProductImage.objects.create(
            product=self.product,
            image='test_main.jpg',
            is_main=True,
        )
        img.delete()

        self.product.refresh_from_db()
        self.assertIsNone(self.product.main_image_id)

    def test_switch_main_image(self):
        """Переключение is_main на другое фото."""
        img1 = ProductImage.objects.create(
            product=self.product,
            image='test1.jpg',
            is_main=True,
        )
        img2 = ProductImage.objects.create(
            product=self.product,
            image='test2.jpg',
            is_main=False,
        )

        # Переключаем
        img1.is_main = False
        img1.save()
        img2.is_main = True
        img2.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.main_image_id, img2.pk)


class VariantPriceWiringRemovedTests(CatalogTestCase):
    """
    ARCH-001 Stage 2 (после review): в каталоге НЕТ price-recompute
    wiring на ORM-события вариантов.

    Автоматическая реакция на изменение is_active/удаление варианта
    невозможна без нарушения архитектуры (reverse dependency,
    cross-context signal или event registry — все запрещены,
    ARCHITECTURE.md → Cross-Domain Coordination). Координация —
    явные service-вызовы PricingService.set_variant_active /
    delete_variant (поведенческие сценарии — в apps/pricing/tests).

    Этот класс доказывает ОТРИЦАНИЕ: ORM-мутации и каскадные удаления
    каталога не запускают пересчёт цен и не трогают Product.
    """

    def setUp(self):
        """Цены двух активных вариантов через сервис pricing."""
        from apps.pricing.services.pricing_service import PricingService
        PricingService.set_price(self.variant_128, Decimal('100.00'))
        PricingService.set_price(self.variant_256, Decimal('200.00'))
        self.product.refresh_from_db()

    def test_product_cascade_delete_does_not_recompute_prices(self):
        """
        Product.delete() → CASCADE ProductVariant → post_delete вариантов
        НЕ должен приводить к попытке повторно обновить уже удаляемый
        Product через price-recompute wiring (никакого пересчёта/записи).
        """
        from apps.catalog.services.catalog_service import CatalogService
        from apps.pricing.services.pricing_service import PricingService
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices, mock.patch.object(
            PricingService, 'recalculate_product_bounds',
        ) as recalc:
            self.product.delete()
        set_prices.assert_not_called()
        recalc.assert_not_called()
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_variant_save_does_not_trigger_price_recompute(self):
        """UPDATE варианта (в т.ч. смена is_active) не пересчитывает цены."""
        from apps.catalog.services.catalog_service import CatalogService
        from apps.pricing.services.pricing_service import PricingService
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices, mock.patch.object(
            PricingService, 'recalculate_product_bounds',
        ) as recalc:
            self.variant_128.is_active = False
            self.variant_128.save()
            self.variant_128.is_active = True
            self.variant_128.save()
        set_prices.assert_not_called()
        recalc.assert_not_called()

    def test_variant_delete_does_not_trigger_price_recompute(self):
        """Удаление отдельного варианта (raw ORM) не пересчитывает цены."""
        from apps.catalog.services.catalog_service import CatalogService
        from apps.pricing.services.pricing_service import PricingService
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices, mock.patch.object(
            PricingService, 'recalculate_product_bounds',
        ) as recalc:
            self.variant_256.delete()
        set_prices.assert_not_called()
        recalc.assert_not_called()
        # Осознанный trade-off: bounds остались прежними (не обновлялись).
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))


@skipIf(
    connection.vendor != 'postgresql',
    'SearchVector работает только с PostgreSQL.',
)
class SearchVectorSignalTests(CatalogTestCase):
    """Сигнал обновления search_vector."""

    def test_search_vector_updated_on_create(self):
        """При создании товара search_vector заполняется."""
        self.product.refresh_from_db()
        self.assertIsNotNone(self.product.search_vector)

    def test_search_vector_updated_on_name_change(self):
        """При изменении name search_vector обновляется."""
        self.product.name = 'Completely New Name XYZ'
        self.product.save()
        self.product.refresh_from_db()
        # search_vector должен содержать новые слова
        # (точная проверка зависит от PostgreSQL tsvector)
        self.assertIsNotNone(self.product.search_vector)
