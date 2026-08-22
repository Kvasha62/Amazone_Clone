# ────────────────────────────────────────────────────────────────────────
# apps/reviews/urls.py
#
#   GET/POST   /api/v1/reviews/               — список / создание
#   GET/PATCH  /api/v1/reviews/{id}/          — детали / обновление
#   DELETE     /api/v1/reviews/{id}/          — удаление
#   POST       /api/v1/reviews/{id}/helpful/  — голос за полезность
# ────────────────────────────────────────────────────────────────────────

from django.urls import path

from apps.reviews.api_views import ReviewDetailView, ReviewHelpfulView, ReviewListView

app_name = 'reviews'

urlpatterns = [
    path('', ReviewListView.as_view(), name='review-list'),
    path('<int:review_id>/', ReviewDetailView.as_view(), name='review-detail'),
    path('<int:review_id>/helpful/', ReviewHelpfulView.as_view(), name='review-helpful'),
]
