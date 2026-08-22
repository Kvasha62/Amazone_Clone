# ────────────────────────────────────────────────────────────────────────
# apps/reviews/tests/test_services.py
#
# Тесты бизнес-логики отзывов:
#   create, update, delete, approve/reject, vote_helpful (toggle)
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.test import TestCase

from rest_framework.exceptions import NotFound, ValidationError

from apps.catalog.tests.factories import CatalogTestCase
from apps.orders.tests.factories import create_test_user
from apps.reviews.models import Review, ReviewHelpfulVote
from apps.reviews.services.review_service import ReviewService
from apps.reviews.tests.factories import create_test_review


class CreateReviewServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()

    def test_create_review_success(self):
        review = ReviewService.create_review(
            user=self.user,
            product=self.product,
            rating=4,
            text='Отличный телефон, пользуюсь месяц!',
        )
        self.assertEqual(review.rating, 4)
        self.assertTrue(review.is_approved)
        self.assertFalse(review.verified_purchase)

    def test_create_review_updates_product_rating(self):
        ReviewService.create_review(
            user=self.user, product=self.product,
            rating=5, text='Очень понравился, рекомендую!',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('5.00'))
        self.assertEqual(self.product.reviews_count, 1)

    def test_create_review_avg_rating(self):
        user2 = create_test_user()
        ReviewService.create_review(
            user=self.user, product=self.product,
            rating=5, text='Очень понравился, рекомендую!',
        )
        ReviewService.create_review(
            user=user2, product=self.product,
            rating=3, text='Нормальный телефон за свои деньги.',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('4.00'))
        self.assertEqual(self.product.reviews_count, 2)

    def test_create_duplicate_review_fails(self):
        ReviewService.create_review(
            user=self.user, product=self.product,
            rating=5, text='Очень понравился, рекомендую!',
        )
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=3, text='Нормальный телефон за свои деньги.',
            )

    def test_create_review_rating_too_low(self):
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=0, text='Очень понравился, рекомендую!',
            )

    def test_create_review_rating_too_high(self):
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=6, text='Очень понравился, рекомендую!',
            )

    def test_create_review_text_too_short(self):
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.user, product=self.product,
                rating=5, text='Ок',
            )


class UpdateReviewServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.review = create_test_review(
            self.user, self.product, rating=5,
            text='Очень понравился, рекомендую!',
        )

    def test_update_rating(self):
        review = ReviewService.update_review(
            self.review, user=self.user, rating=3,
        )
        self.assertEqual(review.rating, 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('3.00'))

    def test_update_text(self):
        review = ReviewService.update_review(
            self.review, user=self.user,
            text='Обновлённый текст отзыва после месяца использования.',
        )
        self.assertEqual(
            review.text,
            'Обновлённый текст отзыва после месяца использования.',
        )

    def test_update_wrong_user_fails(self):
        other_user = create_test_user()
        with self.assertRaises(NotFound):
            ReviewService.update_review(
                self.review, user=other_user, rating=1,
            )


class DeleteReviewServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.review = create_test_review(
            self.user, self.product, rating=5,
            text='Очень понравился, рекомендую!',
        )

    def test_delete_by_author(self):
        ReviewService.delete_review(self.review, user=self.user)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviews_count, 0)

    def test_delete_by_staff(self):
        staff = create_test_user(is_staff=True)
        ReviewService.delete_review(self.review, user=staff)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())

    def test_delete_by_other_user_fails(self):
        other = create_test_user()
        with self.assertRaises(NotFound):
            ReviewService.delete_review(self.review, user=other)


class ModerationServiceTests(CatalogTestCase):

    def setUp(self):
        self.user = create_test_user()
        self.review = create_test_review(
            self.user, self.product, rating=1,
            text='Ужасный товар, не рекомендую.',
            is_approved=False,
        )

    def test_approve_review(self):
        review = ReviewService.approve_review(self.review)
        self.assertTrue(review.is_approved)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviews_count, 1)

    def test_reject_review(self):
        review = ReviewService.reject_review(self.review)
        self.assertFalse(review.is_approved)


class VoteHelpfulServiceTests(CatalogTestCase):
    """Тесты голосования за полезность отзыва (toggle-логика)."""

    def setUp(self):
        # Автор отзыва
        self.author = create_test_user()
        self.review = create_test_review(
            self.author, self.product, rating=4,
            text='Отличный телефон, пользуюсь месяц!',
        )
        # Голосующий пользователь (не автор отзыва)
        self.voter = create_test_user()

    # ── Первый голос ──

    def test_first_vote_yes(self):
        """Первый голос 'yes' → helpful_yes=1, helpful_no=0."""
        review = ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        self.assertEqual(review.helpful_yes, 1)
        self.assertEqual(review.helpful_no, 0)

    def test_first_vote_no(self):
        """Первый голос 'no' → helpful_yes=0, helpful_no=1."""
        review = ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        self.assertEqual(review.helpful_yes, 0)
        self.assertEqual(review.helpful_no, 1)

    def test_first_vote_creates_record(self):
        """Первый голос создаёт ReviewHelpfulVote."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        self.assertEqual(ReviewHelpfulVote.objects.count(), 1)
        vote_obj = ReviewHelpfulVote.objects.first()
        self.assertEqual(vote_obj.user_id, self.voter.pk)
        self.assertEqual(vote_obj.review_id, self.review.pk)
        self.assertEqual(vote_obj.vote, 'yes')

    # ── Toggle off (повторный тот же голос = отмена) ──

    def test_toggle_off_yes(self):
        """Повторный 'yes' → toggle off: helpful_yes=0."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        review = ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        self.assertEqual(review.helpful_yes, 0)
        self.assertEqual(review.helpful_no, 0)

    def test_toggle_off_no(self):
        """Повторный 'no' → toggle off: helpful_no=0."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        review = ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        self.assertEqual(review.helpful_yes, 0)
        self.assertEqual(review.helpful_no, 0)

    def test_toggle_off_deletes_record(self):
        """Toggle off удаляет ReviewHelpfulVote."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        self.assertEqual(ReviewHelpfulVote.objects.count(), 0)

    # ── Переключение (yes→no или no→yes) ──

    def test_switch_yes_to_no(self):
        """Переключение yes→no: helpful_yes=0, helpful_no=1."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        review = ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        self.assertEqual(review.helpful_yes, 0)
        self.assertEqual(review.helpful_no, 1)

    def test_switch_no_to_yes(self):
        """Переключение no→yes: helpful_yes=1, helpful_no=0."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        review = ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        self.assertEqual(review.helpful_yes, 1)
        self.assertEqual(review.helpful_no, 0)

    def test_switch_updates_record(self):
        """Переключение обновляет запись, не создаёт новую."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        self.assertEqual(ReviewHelpfulVote.objects.count(), 1)
        vote_obj = ReviewHelpfulVote.objects.first()
        self.assertEqual(vote_obj.vote, 'no')

    # ── Разные пользователи ──

    def test_different_users_independent(self):
        """Разные пользователи голосуют независимо."""
        voter2 = create_test_user()
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        review = ReviewService.vote_helpful(self.review, user=voter2, vote='no')
        self.assertEqual(review.helpful_yes, 1)
        self.assertEqual(review.helpful_no, 1)
        self.assertEqual(ReviewHelpfulVote.objects.count(), 2)

    # ── Автор не может голосовать за свой отзыв ──

    def test_author_cannot_vote_own_review(self):
        """Автор отзыва не может голосовать за свой же отзыв."""
        with self.assertRaises(ValidationError) as ctx:
            ReviewService.vote_helpful(self.review, user=self.author, vote='yes')
        self.assertIn('свой', str(ctx.exception))

    # ── Валидация ──

    def test_invalid_vote_value(self):
        """Некорректный голос — ValidationError."""
        with self.assertRaises(ValidationError):
            ReviewService.vote_helpful(self.review, user=self.voter, vote='maybe')

    # ── get_user_vote ──

    def test_get_user_vote_none(self):
        """Пользователь ещё не голосовал → None."""
        result = ReviewService.get_user_vote(self.review, self.voter)
        self.assertIsNone(result)

    def test_get_user_vote_yes(self):
        """Пользователь голосовал 'yes' → 'yes'."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        result = ReviewService.get_user_vote(self.review, self.voter)
        self.assertEqual(result, 'yes')

    def test_get_user_vote_after_toggle_off(self):
        """После toggle off → None."""
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        result = ReviewService.get_user_vote(self.review, self.voter)
        self.assertIsNone(result)

    # ── Сложные сценарии ──

    def test_vote_toggle_switch_toggle(self):
        """yes → toggle off → no → switch to yes."""
        r = ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        self.assertEqual(r.helpful_yes, 1)

        r = ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')  # toggle off
        self.assertEqual(r.helpful_yes, 0)

        r = ReviewService.vote_helpful(self.review, user=self.voter, vote='no')
        self.assertEqual(r.helpful_no, 1)

        r = ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')  # switch
        self.assertEqual(r.helpful_yes, 1)
        self.assertEqual(r.helpful_no, 0)

    def test_helpful_score(self):
        """helpful_score = helpful_yes - helpful_no."""
        voter2 = create_test_user()
        voter3 = create_test_user()
        ReviewService.vote_helpful(self.review, user=self.voter, vote='yes')
        ReviewService.vote_helpful(self.review, user=voter2, vote='yes')
        ReviewService.vote_helpful(self.review, user=voter3, vote='no')
        self.review.refresh_from_db()
        self.assertEqual(self.review.helpful_score, 1)  # 2 - 1
