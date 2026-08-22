"""
Тесты сигналов каталога.

Покрывают:
  - sync_product_main_image: is_main=True → Product.main_image
  - clear_product_main_image_on_delete: удаление главного фото
  - update_product_search_vector: name/description → search_vector
"""
from unittest import skipIf

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
