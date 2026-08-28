"""
Тесты PricingService.
"""
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Product
from apps.catalog.services.catalog_service import CatalogService
from apps.pricing.models import Price, PriceHistory
from apps.pricing.services.pricing_service import PricingService
from apps.pricing.tests.factories import PricingTestCase


class SetPriceTests(PricingTestCase):

    def test_set_price_creates_new(self):
        price = PricingService.set_price(
            self.variant_a, Decimal('100.00'),
        )
        self.assertEqual(price.price, Decimal('100.00'))
        self.assertIsNone(price.sale_price)

    def test_set_price_updates_existing(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        price = PricingService.set_price(self.variant_a, Decimal('90.00'))
        self.assertEqual(price.price, Decimal('90.00'))

    def test_set_price_with_sale(self):
        price = PricingService.set_price(
            self.variant_a, Decimal('100.00'),
            sale_price=Decimal('80.00'),
        )
        self.assertEqual(price.sale_price, Decimal('80.00'))

    def test_set_price_zero_rejected(self):
        with self.assertRaises(ValidationError):
            PricingService.set_price(self.variant_a, Decimal('0.00'))

    def test_set_price_negative_rejected(self):
        with self.assertRaises(ValidationError):
            PricingService.set_price(self.variant_a, Decimal('-10.00'))

    def test_sale_price_gt_price_rejected(self):
        with self.assertRaises(ValidationError):
            PricingService.set_price(
                self.variant_a, Decimal('50.00'),
                sale_price=Decimal('60.00'),
            )

    def test_update_creates_history(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(
            self.variant_a, Decimal('90.00'),
            reason='Скидка',
        )
        history = PriceHistory.objects.filter(variant=self.variant_a)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().old_price, Decimal('100.00'))
        self.assertEqual(history.first().new_price, Decimal('90.00'))

    def test_first_set_no_history(self):
        """Первая установка цены не создаёт историю."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        self.assertEqual(
            PriceHistory.objects.filter(variant=self.variant_a).count(), 0,
        )


class RecalculateProductPricesTests(PricingTestCase):

    def test_min_max_set(self):
        """min_price / max_price обновляются на Product."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))

        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_min_max_updated_on_change(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))

        PricingService.set_price(self.variant_a, Decimal('300.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('200.00'))
        self.assertEqual(self.product.max_price, Decimal('300.00'))

    def test_min_max_none_when_no_prices(self):
        """Нет цен → min_price = max_price = None."""
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)

    def test_min_max_excludes_inactive_variants(self):
        """Неактивные варианты не учитываются."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_inactive, Decimal('10.00'))

        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))

    def test_single_price(self):
        """Один вариант с ценой — min = max."""
        PricingService.set_price(self.variant_a, Decimal('150.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('150.00'))
        self.assertEqual(self.product.max_price, Decimal('150.00'))


class GetPriceTests(PricingTestCase):

    def test_get_price_exists(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        price = PricingService.get_price(self.variant_a)
        self.assertIsNotNone(price)
        self.assertEqual(price.price, Decimal('100.00'))

    def test_get_price_not_exists(self):
        price = PricingService.get_price(self.variant_a)
        self.assertIsNone(price)

    def test_get_effective_price_no_sale(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        self.assertEqual(
            PricingService.get_effective_price(self.variant_a),
            Decimal('100.00'),
        )

    def test_get_effective_price_with_sale(self):
        PricingService.set_price(
            self.variant_a, Decimal('100.00'),
            sale_price=Decimal('75.00'),
        )
        self.assertEqual(
            PricingService.get_effective_price(self.variant_a),
            Decimal('75.00'),
        )

    def test_get_effective_price_none(self):
        self.assertIsNone(PricingService.get_effective_price(self.variant_a))


class RemovePriceTests(PricingTestCase):

    def test_remove_price(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.remove_price(self.variant_a)
        self.assertFalse(Price.objects.filter(variant=self.variant_a).exists())

    def test_remove_recalculates_product(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))
        PricingService.remove_price(self.variant_a)

        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('200.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_remove_nonexistent_noop(self):
        """Удаление несуществующей цены — без ошибок."""
        PricingService.remove_price(self.variant_a)


class GetPriceHistoryTests(PricingTestCase):

    def test_history_ordered_by_created_desc(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_a, Decimal('200.00'))
        PricingService.set_price(self.variant_a, Decimal('300.00'))

        history = PricingService.get_price_history(self.variant_a)
        self.assertEqual(history.count(), 2)
        self.assertEqual(history[0].new_price, Decimal('300.00'))
        self.assertEqual(history[1].new_price, Decimal('200.00'))

    def test_history_limit(self):
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_a, Decimal('200.00'))
        history = PricingService.get_price_history(self.variant_a, limit=1)
        self.assertEqual(history.count(), 1)


class PricingCatalogOwnershipTests(PricingTestCase):
    """
    ARCH-001 (Pricing → Catalog ownership).

    Проверяют, что PricingService:
      • НЕ мутирует catalog.Product напрямую;
      • делегирует пересчёт min_price/max_price в CatalogService;
      • не создаёт двойного пересчёта (сигналы удалены).
    """

    def test_set_price_delegates_to_catalog_service(self):
        """set_price вызывает CatalogService.recalculate_product_prices."""
        with mock.patch.object(CatalogService, 'recalculate_product_prices') as m:
            PricingService.set_price(self.variant_a, Decimal('100.00'))
            m.assert_called_once_with(self.product)

    def test_remove_price_delegates_to_catalog_service(self):
        """remove_price вызывает CatalogService.recalculate_product_prices."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        with mock.patch.object(CatalogService, 'recalculate_product_prices') as m:
            PricingService.remove_price(self.variant_a)
            m.assert_called_once_with(self.product)

    def test_no_double_recalculation_on_set(self):
        """set_price пересчитывает min/max ровно один раз (без второстепенного сигнала)."""
        with mock.patch.object(CatalogService, 'recalculate_product_prices') as m:
            PricingService.set_price(self.variant_a, Decimal('100.00'))
            PricingService.set_price(self.variant_a, Decimal('150.00'))
            # Первая установка (create) + второе изменение (update) = 2 вызова,
            # но НИКАКОГО лишнего вызова от signal не происходит.
            self.assertEqual(m.call_count, 2)

    def test_no_double_recalculation_on_remove(self):
        """remove_price пересчитывает min/max ровно один раз."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))
        with mock.patch.object(CatalogService, 'recalculate_product_prices') as m:
            PricingService.remove_price(self.variant_a)
            m.assert_called_once_with(self.product)

    def test_pricing_does_not_directly_mutate_product(self):
        """
        PricingService НЕ вызывает Product.save() напрямую:
        если CatalogService замокать в no-op, то Product.save() не вызывается.
        """
        with mock.patch.object(
            CatalogService, 'recalculate_product_prices', return_value=None,
        ), mock.patch.object(Product, 'save') as product_save:
            PricingService.set_price(self.variant_a, Decimal('100.00'))
            PricingService.set_price(self.variant_b, Decimal('200.00'))
            PricingService.remove_price(self.variant_a)
            product_save.assert_not_called()

    def test_raw_orm_price_creation_does_not_recalculate(self):
        """
        Cross-domain сигналов больше нет: прямое создание Price через ORM
        (в обход PricingService) НЕ пересчитывает каталог.Product.
        Обновление min/max — ответственность CatalogService / PricingService.
        """
        Price.objects.create(variant=self.variant_a, price=Decimal('100.00'))
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)

    def test_set_price_updates_product_via_catalog_contract(self):
        """Конечный эффект: после set_price min/max на товаре корректны."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))
