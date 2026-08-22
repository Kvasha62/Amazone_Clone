# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_signals.py
# ────────────────────────────────────────────────────────────────────────

from django.test import TestCase

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.reviews.tests.factories import create_test_review


class ReviewSignalTests(CatalogTestCase):

    def test_signal_on_create(self):
        user = create_test_user()
        # Сигнал не должен падать
        review = create_test_review(user, self.product)
        self.assertIsNotNone(review.pk)

    def test_signal_on_delete(self):
        user = create_test_user()
        review = create_test_review(user, self.product)
        review.delete()  # Сигнал не должен падать
