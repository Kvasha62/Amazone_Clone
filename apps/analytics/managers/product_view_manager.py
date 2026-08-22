# ────────────────────────────────────────────────────────────────────────
# apps/analytics/managers/product_view_manager.py — менеджер просмотров.
#
# Использует from_queryset для наследования всех методов QuerySet.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
# ────────────────────────────────────────────────────────────────────────

from django.db import models


class ProductViewQuerySet(models.QuerySet):
    """
    Расширенный QuerySet для ProductView.

    Методы:
      for_product(product)  — просмотры конкретного товара
      for_user(user)        — просмотры пользователя
      by_source(source)     — по источнику трафика
      recent(days)          — за последние N дней
      since(date)           — с указанной даты
    """

    def for_product(self, product):
        return self.filter(product=product)

    def for_user(self, user):
        return self.filter(user=user)

    def by_source(self, source):
        return self.filter(source=source)

    def recent(self, days: int = 7):
        """Просмотры за последние N дней."""
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff)

    def since(self, date):
        """Просмотры с указанной даты."""
        return self.filter(created_at__gte=date)


ProductViewManager = models.Manager.from_queryset(ProductViewQuerySet)
