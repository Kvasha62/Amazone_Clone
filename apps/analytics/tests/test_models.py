# ────────────────────────────────────────────────────────────────────────
# apps/analytics/tests/test_models.py — тесты модели ProductView.
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase
from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.analytics.tests.factories import create_test_view
from apps.analytics.models import ProductView


class ProductViewModelTests(CatalogTestCase):

    def test_create_view(self):
        """Создание просмотра."""
        view = create_test_view(self.product)
        self.assertIsNotNone(view.pk)
        self.assertEqual(view.product, self.product)

    def test_create_view_with_user(self):
        """Просмотр авторизованного пользователя."""
        user = create_test_user()
        view = create_test_view(self.product, user=user)
        self.assertEqual(view.user, user)

    def test_create_view_guest(self):
        """Просмотр гостя (без user, с session_key)."""
        view = create_test_view(
            self.product, session_key='abc123', source='organic',
        )
        self.assertIsNone(view.user)
        self.assertEqual(view.session_key, 'abc123')
        self.assertEqual(view.source, 'organic')

    def test_str_user(self):
        """__str__ для авторизованного просмотра."""
        user = create_test_user()
        view = create_test_view(self.product, user=user)
        self.assertIn(f'user#{user.pk}', str(view))

    def test_str_guest(self):
        """__str__ для гостевого просмотра."""
        view = create_test_view(
            self.product, session_key='abcdefgh1234',
        )
        str_repr = str(view)
        self.assertIn(f'product={self.product.pk}', str_repr)

    def test_ordering_desc(self):
        """Просмотры сортируются по -created_at."""
        view = create_test_view(self.product)
        self.assertIsNotNone(view.pk)
        # Самый новый — первый
        self.assertEqual(
            ProductView.objects.first().pk, view.pk,
        )


class ProductViewManagerTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.view1 = create_test_view(self.product, user=self.user)
        # Create a second product for a separate view
        from apps.catalog.models import Product
        from apps.catalog.constants import ProductStatus
        self.other_product = Product.objects.create(
            name='Other Product',
            brand=self.brand,
            primary_category=self.leaf_category,
            status=ProductStatus.ACTIVE,
        )
        self.view2 = create_test_view(self.other_product, session_key='sess1')

    def test_for_product(self):
        """Фильтр по товару."""
        qs = ProductView.objects.for_product(self.product)
        self.assertEqual(qs.count(), 1)

    def test_for_user(self):
        """Фильтр по пользователю."""
        qs = ProductView.objects.for_user(self.user)
        self.assertEqual(qs.count(), 1)

    def test_by_source(self):
        """Фильтр по источнику."""
        create_test_view(self.product, source='organic')
        qs = ProductView.objects.by_source('organic')
        self.assertEqual(qs.count(), 1)

    def test_recent(self):
        """Просмотры за последние N дней."""
        qs = ProductView.objects.recent(days=7)
        self.assertEqual(qs.count(), 2)

    def test_since(self):
        """Просмотры с указанной даты."""
        from django.utils import timezone
        qs = ProductView.objects.since(
            timezone.now() - timezone.timedelta(days=1),
        )
        self.assertEqual(qs.count(), 2)
