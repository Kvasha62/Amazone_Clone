"""
Тесты PricingService.
"""
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.exceptions import ValidationError

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

    Проверяют архитектуру зависимости:
      pricing → CatalogService.set_product_prices → catalog.Product

    Без обратной зависимости catalog → pricing и без двойного пересчёта.
    """

    def test_set_price_passes_computed_bounds_to_catalog(self):
        """
        set_price САМ рассчитывает min/max и передаёт готовые значения
        в CatalogService.set_product_prices (не мутирует Product.save()).
        """
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            PricingService.set_price(self.variant_a, Decimal('100.00'))
            set_prices.assert_called_once_with(
                self.product,
                min_price=Decimal('100.00'),
                max_price=Decimal('100.00'),
            )

    def test_remove_price_passes_computed_bounds_to_catalog(self):
        """remove_price также передаёт рассчитанные границы в каталог."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            PricingService.remove_price(self.variant_a)
            set_prices.assert_called_once_with(
                self.product,
                min_price=Decimal('200.00'),
                max_price=Decimal('200.00'),
            )

    def test_set_price_recomputes_exactly_once(self):
        """set_price пересчитывает min/max ровно один раз (без сигнального дубля)."""
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            PricingService.set_price(self.variant_a, Decimal('100.00'))
            # create → ровно 1 вызов каталога, никакого второго от signal.
            self.assertEqual(set_prices.call_count, 1)

    def test_update_price_recomputes_exactly_once(self):
        """Обновление существующей цены — тоже ровно один пересчёт."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            PricingService.set_price(self.variant_a, Decimal('150.00'))
            self.assertEqual(set_prices.call_count, 1)

    def test_remove_price_recomputes_exactly_once(self):
        """remove_price пересчитывает min/max ровно один раз."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            PricingService.remove_price(self.variant_a)
            set_prices.assert_called_once()

    def test_raw_orm_price_creation_does_not_recalculate(self):
        """
        Cross-domain сигналов больше нет: прямое создание Price через ORM
        (в обход PricingService) НЕ пересчитывает каталог.Product.
        Обновление min/max — ответственность PricingService / CatalogService.
        """
        Price.objects.create(variant=self.variant_a, price=Decimal('100.00'))
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)

    def test_set_price_updates_product_via_catalog_contract(self):
        """Реальный путь: после set_price min/max на товаре корректны."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_b, Decimal('200.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_only_active_variants_are_used_in_bounds(self):
        """Неактивные варианты не участвуют в расчёте (только ACTIVE)."""
        PricingService.set_price(self.variant_a, Decimal('100.00'))
        PricingService.set_price(self.variant_inactive, Decimal('10.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))

    def test_no_prices_sets_none(self):
        """Отсутствие цен → min_price = max_price = None."""
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)


class RecalculateProductBoundsTests(PricingTestCase):
    """
    ARCH-001 Stage 2: публичный контракт
    PricingService.recalculate_product_bounds().

    Единственный владелец расчёта price bounds — pricing. Контракт
    вызывается из catalog (price-relevant события вариантов) через
    register_price_bounds_listener — без Django-сигналов между
    контекстами и без импорта pricing из catalog.
    """

    def _raw_price(self, variant, price):
        """Создаёт Price напрямую через ORM (в обход set_price)."""
        return Price.objects.create(variant=variant, price=price)

    def test_sets_bounds_from_active_variants(self):
        """min/max считаются из цен активных вариантов."""
        self._raw_price(self.variant_a, Decimal('100.00'))
        self._raw_price(self.variant_b, Decimal('300.00'))
        PricingService.recalculate_product_bounds(self.product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('300.00'))

    def test_excludes_inactive_variants(self):
        """Неактивные варианты не участвуют в расчёте границ."""
        self._raw_price(self.variant_a, Decimal('100.00'))
        self._raw_price(self.variant_inactive, Decimal('10.00'))
        PricingService.recalculate_product_bounds(self.product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))

    def test_no_prices_sets_none(self):
        """Нет цен → min_price = max_price = None."""
        PricingService.recalculate_product_bounds(self.product)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)

    def test_writes_through_catalog_contract(self):
        """Запись идёт через CatalogService.set_product_prices (ровно 1)."""
        self._raw_price(self.variant_a, Decimal('150.00'))
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            PricingService.recalculate_product_bounds(self.product)
        set_prices.assert_called_once_with(
            self.product,
            min_price=Decimal('150.00'),
            max_price=Decimal('150.00'),
        )

    def test_pricing_registered_as_price_bounds_listener(self):
        """
        Wiring ARCH-001 Stage 2: pricing подписан на price-relevant
        события каталога (регистрация в PricingConfig.ready()).
        """
        from apps.catalog.services import catalog_service
        self.assertIn(
            PricingService.recalculate_product_bounds,
            catalog_service._price_bounds_listeners,
        )

    def test_catalog_notification_reaches_pricing_recalc(self):
        """
        Интеграционный путь контракта: notify_price_relevant_state_changed()
        из catalog доходит до пересчёта в pricing и обновляет Product
        (без Django-сигналов между контекстами).
        """
        from apps.catalog.services.catalog_service import (
            notify_price_relevant_state_changed,
        )
        self._raw_price(self.variant_a, Decimal('100.00'))
        self._raw_price(self.variant_b, Decimal('300.00'))
        # Состояние варианта изменилось (в тестах имитируем напрямую).
        notify_price_relevant_state_changed(self.product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('300.00'))
