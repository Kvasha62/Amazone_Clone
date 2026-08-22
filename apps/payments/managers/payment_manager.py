# ────────────────────────────────────────────────────────────────────────
# apps/payments/managers/payment_manager.py — менеджер для Payment.
#
# Подмешивает PaymentQuerySet-методы в Payment.objects:
#   Payment.objects.pending()
#   Payment.objects.for_user(user).succeeded()
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#from-queryset
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.payments.querysets.payment_queryset import PaymentQuerySet


class PaymentManager(models.Manager.from_queryset(PaymentQuerySet)):
    """
    Менеджер Payment с QuerySet-методами.
    """
    pass
