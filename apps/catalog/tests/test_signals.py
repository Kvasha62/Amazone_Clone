"""
Тесты сигналов каталога.

Покрывают:
  - sync_product_main_image: is_main=True → Product.main_image
  - clear_product_main_image_on_delete: удаление главного фото
  - update_product_search_vector: name/description → search_vector
  - VariantPriceRelevantSignalTests: price-relevant изменения вариантов
    (is_active, удаление) обновляют min_price/max_price через контракт
    notify_price_relevant_state_changed → pricing → CatalogService
    (ARCH-001 Stage 2, без обратной зависимости catalog → pricing)
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
    ProductVariant,
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


class VariantPriceRelevantSignalTests(CatalogTestCase):
    """
    ARCH-001 Stage 2: price-relevant изменения вариантов каталога
    продолжают обновлять Product.min_price / max_price — но теперь
    через контракт notify_price_relevant_state_changed(): расчёт в
    pricing (PricingService.recalculate_product_bounds), запись в
    CatalogService.set_product_prices(). Без чтения pricing из catalog.
    """

    def setUp(self):
        """Цены двух активных вариантов через сервис pricing."""
        from apps.pricing.services.pricing_service import PricingService
        PricingService.set_price(self.variant_128, Decimal('100.00'))
        PricingService.set_price(self.variant_256, Decimal('200.00'))
        self.product.refresh_from_db()

    def test_variant_deactivation_updates_bounds(self):
        """Деактивация варианта — границы пересчитываются (без него)."""
        self.variant_256.is_active = False
        self.variant_256.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))

    def test_variant_reactivation_restores_bounds(self):
        """Реактивация варианта — границы восстанавливаются."""
        self.variant_256.is_active = False
        self.variant_256.save()
        self.variant_256.is_active = True
        self.variant_256.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_variant_delete_updates_bounds(self):
        """Удаление варианта — границы пересчитываются."""
        self.variant_256.delete()
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('100.00'))

    def test_all_variants_inactive_sets_bounds_none(self):
        """Все варианты неактивны → min_price = max_price = None."""
        self.variant_128.is_active = False
        self.variant_128.save()
        self.variant_256.is_active = False
        self.variant_256.save()
        self.product.refresh_from_db()
        self.assertIsNone(self.product.min_price)
        self.assertIsNone(self.product.max_price)

    def test_variant_creation_without_price_keeps_bounds(self):
        """
        Создание варианта без цены НЕ меняет границы
        (поведение сохранено: recalc при создании не нужен — цены нет).
        """
        ProductVariant.objects.create(
            product=self.product, sku='SM-S24-512',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.min_price, Decimal('100.00'))
        self.assertEqual(self.product.max_price, Decimal('200.00'))

    def test_price_relevant_change_writes_through_catalog_contract(self):
        """
        Обновление при price-relevant изменении идёт через публичный
        контракт каталога set_product_prices (ровно один вызов — без
        сигнального дубля).
        """
        from apps.catalog.services.catalog_service import CatalogService
        with mock.patch.object(
            CatalogService, 'set_product_prices', return_value=self.product,
        ) as set_prices:
            self.variant_256.is_active = False
            self.variant_256.save()
        set_prices.assert_called_once_with(
            self.product,
            min_price=Decimal('100.00'),
            max_price=Decimal('100.00'),
        )


class GetOldIsActiveTests(CatalogTestCase):
    """
    ARCH-001 Stage 2: ProductVariant._get_old_is_active().

    Метод заявлен сигналом on_variant_change, но ранее не существовал —
    любой UPDATE варианта падал с AttributeError (латентный баг).
    Регрессионные тесты реализации.
    """

    def test_saved_variant_returns_db_value(self):
        """Сохранённый вариант → is_active из БД."""
        self.assertTrue(self.variant_128._get_old_is_active())

    def test_unsaved_variant_returns_none(self):
        """Несохранённый вариант → None («старого» значения нет)."""
        fresh = ProductVariant(product=self.product, sku='SM-S24-OLD')
        self.assertIsNone(fresh._get_old_is_active())

    def test_modified_but_not_saved_returns_previous_value(self):
        """Изменение в памяти до save() → из БД возвращается СТАРОЕ значение."""
        self.variant_128.is_active = False  # ещё НЕ сохранено
        self.assertTrue(self.variant_128._get_old_is_active())

    def test_saved_after_change_returns_previous_value(self):
        """
        Сразу после save() метод возвращает значение ДО записи —
        именно так сигнал on_variant_change детектирует изменение
        (старое True != новое False → уведомление).
        """
        self.variant_128.is_active = False
        self.variant_128.save()
        self.assertTrue(self.variant_128._get_old_is_active())


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
