# ────────────────────────────────────────────────────────────────────────
# apps/payments/admin/__init__.py — реэкспорт admin-классов.
# ────────────────────────────────────────────────────────────────────────

from apps.payments.admin.payment_admin import PaymentAdmin, PaymentEventInline

__all__ = ['PaymentAdmin', 'PaymentEventInline']
