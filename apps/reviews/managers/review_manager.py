from django.db import models

from apps.reviews.querysets.review_queryset import ReviewQuerySet


class ReviewManager(models.Manager.from_queryset(ReviewQuerySet)):
    pass
