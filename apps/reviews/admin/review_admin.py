from django.contrib import admin

from apps.reviews.models import Review


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
