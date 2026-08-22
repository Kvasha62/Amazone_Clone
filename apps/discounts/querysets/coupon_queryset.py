from django.db import models
from django.utils import timezone


class CouponQuerySet(models.QuerySet):

    def active(self):
        return self.filter(is_active=True)

    def valid_now(self):
        """Активные купоны, чей срок действия сейчас."""
        now = timezone.now()
        return self.filter(
            is_active=True,
            started_at__lte=now,
            ended_at__gte=now,
        )

    def not_exhausted(self):
        """Купоны с оставшимися использованиями (или без лимита)."""
        return self.filter(
            models.Q(max_total_uses=0) | models.Q(times_used__lt=models.F('max_total_uses'))
        )

    def for_campaign(self, campaign):
        return self.filter(campaign=campaign)

    def percent_type(self):
        return self.filter(discount_type='percent')

    def fixed_type(self):
        return self.filter(discount_type='fixed')

    def with_campaign(self):
        return self.select_related('campaign')
