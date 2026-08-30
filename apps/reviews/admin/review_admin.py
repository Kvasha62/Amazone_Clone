from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.reviews.models import Review, ReviewHelpfulVote


# ARCH-001 H2: fields whose changes can move Product.rating /
# Product.reviews_count. The Product aggregate write still goes through
# ReviewService.recalculate_product_rating() → CatalogService.set_review_stats().
REVIEW_AGGREGATE_SOURCE_FIELDS = ('product', 'rating', 'is_approved')

# There is no existing service-level operation for moving an existing review
# between users/products. In Admin change forms we therefore keep those fields
# read-only instead of inventing domain logic in Admin.
REVIEW_ADMIN_IMMUTABLE_CHANGE_FIELDS = ('user', 'product')

# Review-owned fields that are outside the Product aggregate contract and are
# not covered by the existing create/update/moderation ReviewService methods.
# Keeping this list explicit prevents ModelAdmin.save_model() from falling back
# to a full model save that would persist aggregate-source fields in parallel
# with ReviewService.
REVIEW_ADMIN_DIRECT_FIELDS = (
    'verified_purchase',
    'helpful_yes',
    'helpful_no',
)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'product', 'user', 'rating',
        'verified_purchase', 'is_approved', 'created_at',
    )
    list_filter = ('rating', 'is_approved', 'verified_purchase')
    search_fields = ('text', 'title', 'user__email', 'product__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'product')
    list_per_page = 50
    ordering = ('-created_at',)

    actions = ['approve_selected', 'reject_selected']

    def get_readonly_fields(self, request, obj=None):
        """Existing reviews cannot be moved to another user/product in Admin."""
        fields = tuple(super().get_readonly_fields(request, obj))
        if obj is not None:
            return fields + REVIEW_ADMIN_IMMUTABLE_CHANGE_FIELDS
        return fields

    def save_model(self, request, obj, form, change):
        """Route aggregate-affecting Review Admin saves through ReviewService.

        ``rating`` and ``is_approved`` feed Product.rating /
        Product.reviews_count, so saving them with the default ModelAdmin path
        would bypass the ARCH-001 service-level aggregate contract. New Review
        rows are created through ``ReviewService.create_review()``; existing
        rating/text/title changes go through ``update_review()`` and approval
        changes go through ``approve_review()`` / ``reject_review()``.
        Review-owned fields outside those service methods and outside the
        product aggregate contract are saved with an explicit ``update_fields``
        list so aggregate-source fields are not written a second way.
        """
        from apps.reviews.services.review_service import ReviewService

        if not change:
            with transaction.atomic():
                saved_review = ReviewService.create_review(
                    user=obj.user,
                    product=obj.product,
                    rating=obj.rating,
                    text=obj.text,
                    title=obj.title,
                )
                if not obj.is_approved:
                    saved_review = ReviewService.reject_review(saved_review)
                self._save_direct_review_fields(saved_review, obj)
                saved_review.refresh_from_db()
                self._copy_review_state(obj, saved_review)
            return

        previous = Review.objects.select_related('user', 'product').get(pk=obj.pk)
        if obj.user_id != previous.user_id:
            raise PermissionDenied(
                'Изменение автора Review через Admin запрещено (ARCH-001 H2): '
                'для переноса отзыва на другого пользователя нет '
                'service-level операции.'
            )
        if obj.product_id != previous.product_id:
            raise PermissionDenied(
                'Изменение Review.product через Admin запрещено (ARCH-001 H2): '
                'перенос отзыва между товарами меняет Product.rating / '
                'reviews_count и не имеет отдельного service-level пути.'
            )

        with transaction.atomic():
            saved_review = previous
            service_changes = {}
            if obj.rating != previous.rating:
                service_changes['rating'] = obj.rating
            if obj.text != previous.text:
                service_changes['text'] = obj.text
            if obj.title != previous.title:
                service_changes['title'] = obj.title

            if service_changes:
                saved_review = ReviewService.update_review(
                    previous,
                    user=previous.user,
                    **service_changes,
                )

            if obj.is_approved != saved_review.is_approved:
                if obj.is_approved:
                    saved_review = ReviewService.approve_review(saved_review)
                else:
                    saved_review = ReviewService.reject_review(saved_review)

            self._save_direct_review_fields(saved_review, obj)
            saved_review.refresh_from_db()
            self._copy_review_state(obj, saved_review)

    def delete_model(self, request, obj):
        """Single Review deletion affects aggregates and must use the service."""
        from apps.reviews.services.review_service import ReviewService

        ReviewService.delete_review(obj, user=request.user)

    def delete_queryset(self, request, queryset):
        """Bulk Review deletion also affects aggregates; route per row."""
        from apps.reviews.services.review_service import ReviewService

        for review in queryset.select_related('user', 'product'):
            ReviewService.delete_review(review, user=request.user)

    def _save_direct_review_fields(self, saved_review, submitted_review):
        update_fields = []
        for field in REVIEW_ADMIN_DIRECT_FIELDS:
            submitted_value = getattr(submitted_review, field)
            if getattr(saved_review, field) != submitted_value:
                setattr(saved_review, field, submitted_value)
                update_fields.append(field)

        if update_fields:
            saved_review.save(update_fields=[*update_fields, 'updated_at'])

    def _copy_review_state(self, target, source):
        for field in target._meta.concrete_fields:
            setattr(target, field.attname, getattr(source, field.attname))

    @admin.action(description='Одобрить выбранные')
    def approve_selected(self, request, queryset):
        from apps.reviews.services.review_service import ReviewService
        for review in queryset:
            ReviewService.approve_review(review)
        self.message_user(request, f'Одобрено {queryset.count()} отзывов.')

    @admin.action(description='Отклонить выбранные')
    def reject_selected(self, request, queryset):
        from apps.reviews.services.review_service import ReviewService
        for review in queryset:
            ReviewService.reject_review(review)
        self.message_user(request, f'Отклонено {queryset.count()} отзывов.')


@admin.register(ReviewHelpfulVote)
class ReviewHelpfulVoteAdmin(admin.ModelAdmin):
    """Админка для голосов за полезность отзывов."""
    list_display = ('id', 'user', 'review', 'vote', 'created_at')
    list_filter = ('vote',)
    raw_id_fields = ('user', 'review')
    list_per_page = 50
    ordering = ('-created_at',)
