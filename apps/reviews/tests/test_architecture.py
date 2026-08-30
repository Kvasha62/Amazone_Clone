# ────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_architecture.py
#
# ARCH-001 Stage C1 — ownership-контракт агрегатов отзывов:
#
#   ReviewService.recalculate_product_rating()
#     → рассчитывает AVG/COUNT по СВОИМ Review
#     → CatalogService.set_review_stats(product, ...)
#     → catalog.Product.rating / reviews_count
#
# Чему посвящены тесты:
#   A. CatalogService.set_review_stats существует и реально пишет
#      поля каталога (+ валидация значений).
#   B. ReviewService использует catalog-контракт, а не прямую
#      мутацию / прежний Product.update_rating().
#   C. Зависимости catalog → reviews в production runtime нет.
#   D. Единственный service-level writer агрегатов —
#      CatalogService.set_review_stats (файловый скан на прямые
#      присвоения/QuerySet.update в обход контракта).
#      Скан защищает кодовый путь; декларативные Admin-поверхности
#      (форма товара) им не покрываются — это residual H3,
#      hardening вне этапа C1.
#
# Методика (как в apps/discounts/tests/test_architecture.py):
#   • source-inspection (inspect.getsource) для сервисных контрактов;
#   • файловый скан production-кода; tests / migrations / management
#     (seed) НЕ считаются production runtime dependency — так же,
#     как принято в ARCH-001 аудите Stage 2/3.
# ────────────────────────────────────────────────────────────────

import inspect
import os
import re
from decimal import Decimal

from django.test import SimpleTestCase

from rest_framework.exceptions import ValidationError

from apps.catalog.models import Product
from apps.catalog.services.catalog_service import CatalogService
from apps.catalog.tests.factories import CatalogTestCase
from apps.reviews.services.review_service import ReviewService
from apps.reviews import signals as reviews_signals

# Корень репозитория: apps/reviews/tests/test_architecture.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Каталоги, не являющиеся production runtime (методика ARCH-001).
_NON_RUNTIME_DIRS = {'tests', 'migrations', 'management', '__pycache__'}


def _iter_production_py_files(app_path: str):
    """Все .py файлы приложения, кроме tests/migrations/management."""
    for dirpath, dirnames, filenames in os.walk(app_path):
        dirnames[:] = [d for d in dirnames if d not in _NON_RUNTIME_DIRS]
        for filename in filenames:
            if filename.endswith('.py'):
                yield os.path.join(dirpath, filename)


class CatalogSetReviewStatsTests(CatalogTestCase):
    """A. CatalogService.set_review_stats — реальный writer полей."""

    def test_set_review_stats_updates_product_fields(self):
        product = CatalogService.set_review_stats(
            self.product,
            rating=Decimal('4.50'),
            reviews_count=12,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('4.50'))
        self.assertEqual(self.product.reviews_count, 12)
        self.assertEqual(product.pk, self.product.pk)

    def test_set_review_stats_accepts_zero_values(self):
        """Товар без одобренных отзывов: 0.00 / 0 — валидное состояние."""
        CatalogService.set_review_stats(
            self.product,
            rating=Decimal('0.00'),
            reviews_count=0,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('0.00'))
        self.assertEqual(self.product.reviews_count, 0)

    def test_set_review_stats_rejects_out_of_bounds_rating(self):
        for bad_rating in (Decimal('-0.01'), Decimal('5.01'), Decimal('6')):
            with self.subTest(rating=bad_rating):
                with self.assertRaises(ValidationError):
                    CatalogService.set_review_stats(
                        self.product,
                        rating=bad_rating,
                        reviews_count=1,
                    )

                self.product.refresh_from_db()
                self.assertEqual(self.product.rating, Decimal('0.00'))
                self.assertEqual(self.product.reviews_count, 0)

    def test_set_review_stats_rejects_non_finite_decimal_values(self):
        """NaN / ±Infinity и непредставимые порядки величины.

        Публичный контракт обязан отвечать предусмотренным
        ValidationError, а не протекать decimal.InvalidOperation
        (сравнение с NaN / quantize бесконечности падают в decimal).
        """
        special_values = (
            Decimal('NaN'),
            Decimal('sNaN'),
            Decimal('Infinity'),
            Decimal('-Infinity'),
            # Конечное, но непредставимое в numeric(3,2) значение.
            Decimal('1E+30'),
        )
        for bad_rating in special_values:
            with self.subTest(rating=bad_rating):
                with self.assertRaises(ValidationError):
                    CatalogService.set_review_stats(
                        self.product,
                        rating=bad_rating,
                        reviews_count=1,
                    )

                self.product.refresh_from_db()
                self.assertEqual(self.product.rating, Decimal('0.00'))
                self.assertEqual(self.product.reviews_count, 0)

    def test_set_review_stats_quantizes_to_two_decimal_places(self):
        """Обычное значение нормализуется до 2 знаков: 4.567 → 4.57."""
        CatalogService.set_review_stats(
            self.product,
            rating=Decimal('4.567'),
            reviews_count=3,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('4.57'))
        self.assertEqual(self.product.reviews_count, 3)

    def test_set_review_stats_rejects_negative_reviews_count(self):
        with self.assertRaises(ValidationError):
            CatalogService.set_review_stats(
                self.product,
                rating=Decimal('3.00'),
                reviews_count=-1,
            )

        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('0.00'))
        self.assertEqual(self.product.reviews_count, 0)

    def test_set_review_stats_touches_only_aggregate_fields(self):
        """Контракт меняет только rating/reviews_count, не весь товар."""
        self.product.name = 'Не должно быть перезаписано'
        self.product.save(update_fields=['name', 'updated_at'])
        # Локальные несохранённые правки, которые контракт НЕ должен
        # случайно закоммитить полным save():
        stale_product = Product.objects.get(pk=self.product.pk)
        stale_product.name = 'stale local edit'

        CatalogService.set_review_stats(
            stale_product,
            rating=Decimal('2.00'),
            reviews_count=1,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Не должно быть перезаписано')
        self.assertEqual(self.product.rating, Decimal('2.00'))
        self.assertEqual(self.product.reviews_count, 1)


class ReviewAggregateContractArchitectureTests(SimpleTestCase):
    """B/D. ReviewService использует контракт; старый путь удалён."""

    def test_recalculate_uses_catalog_contract_not_model_setter(self):
        source = inspect.getsource(ReviewService.recalculate_product_rating)
        self.assertIn('CatalogService.set_review_stats', source)
        # Прежний cross-context path (Product.update_rating) запрещён.
        self.assertNotIn('update_rating', source)

    def test_product_update_rating_method_removed(self):
        """Старый авторитетный путь не должен возродиться вторым writer'ом."""
        self.assertFalse(
            hasattr(Product, 'update_rating'),
            'Product.update_rating() — запрещённый cross-context path '
            '(ARCH-001 C1); writer — CatalogService.set_review_stats().',
        )

    def test_review_service_does_not_directly_mutate_product_aggregates(self):
        source = inspect.getsource(ReviewService)
        forbidden = (
            # Прямое присвоение полей catalog.Product из reviews.
            'product.rating =',
            'product.reviews_count =',
            # ORM-мутации каталога в обход сервиса.
            'Product.objects.filter',
            'Product.objects.update',
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)

    def test_catalog_service_set_review_stats_is_the_writer(self):
        """Контракт действительно пишет агрегаты (сам остаётся writer'ом).

        Отсутствие обращений к reviews гарантирует отдельный файловый
        скан CrossContextDependencyDirectionTests (он включает
        catalog_service.py и запрещает 'apps.reviews' в нём).
        """
        source = inspect.getsource(CatalogService.set_review_stats)
        self.assertIn('product.rating =', source)
        self.assertIn('product.reviews_count =', source)


class CrossContextDependencyDirectionTests(SimpleTestCase):
    """C. catalog → reviews в production runtime не существует."""

    def test_catalog_production_code_does_not_import_reviews(self):
        catalog_dir = os.path.join(_REPO_ROOT, 'apps', 'catalog')
        offenders = []
        for path in _iter_production_py_files(catalog_dir):
            with open(path, encoding='utf-8') as fh:
                source = fh.read()
            if 'apps.reviews' in source or 'from apps import reviews' in source:
                offenders.append(os.path.relpath(path, _REPO_ROOT))

        self.assertEqual(
            offenders,
            [],
            'Запрещённая зависимость catalog → reviews (ARCH-001 C1): '
            f'{offenders}',
        )

    def test_reviews_signals_do_not_mutate_catalog(self):
        """Сигналы reviews — только логирование, не mutation (ARCH-001 §3)."""
        source = inspect.getsource(reviews_signals)
        forbidden = ('CatalogService', 'set_review_stats', '.save(', 'update_rating')
        for token in forbidden:
            self.assertNotIn(token, source, token)


class SingleServiceWriterScanTests(SimpleTestCase):
    """D. Файловый скан: на сервисном уровне агрегаты пишет только catalog.

    Сканируется production-код на прямые присвоения/QuerySet.update
    в обход CatalogService.set_review_stats(). Декларативные
    Admin-поверхности (например, форма товара) этим сканом не
    покрываются — известный residual H3, hardening вне этапа C1.
    """

    # Разрешённый авторитетный service-level writer (путь от корня репо).
    AUTHORITATIVE_WRITER = os.path.join(
        'apps', 'catalog', 'services', 'catalog_service.py',
    )

    FORBIDDEN_PATTERNS = (
        # Прямое присвоение полей агрегатов у объекта product.
        re.compile(r'product\.rating\s*='),
        re.compile(r'product\.reviews_count\s*='),
        # QuerySet.update в обход сервисного контракта.
        re.compile(r'\.update\(\s*[^)]*\brating\s*='),
        re.compile(r'\.update\(\s*[^)]*\breviews_count\s*='),
    )

    def test_no_second_service_level_writer_for_review_aggregates(self):
        apps_dir = os.path.join(_REPO_ROOT, 'apps')
        offenders = []

        for app_name in sorted(os.listdir(apps_dir)):
            app_path = os.path.join(apps_dir, app_name)
            if not os.path.isdir(app_path):
                continue
            for path in _iter_production_py_files(app_path):
                rel_path = os.path.normpath(
                    os.path.relpath(path, _REPO_ROOT),
                )
                if rel_path == os.path.normpath(self.AUTHORITATIVE_WRITER):
                    continue
                with open(path, encoding='utf-8') as fh:
                    source = fh.read()
                for pattern in self.FORBIDDEN_PATTERNS:
                    if pattern.search(source):
                        offenders.append(
                            f'{rel_path}: {pattern.pattern}',
                        )

        self.assertEqual(
            offenders,
            [],
            'Обход CatalogService.set_review_stats() для записи '
            'Product.rating / Product.reviews_count (ARCH-001 C1): '
            f'{offenders}',
        )
