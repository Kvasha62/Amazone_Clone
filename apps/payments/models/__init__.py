# ────────────────────────────────────────────────────────────────────────
# apps/payments/models/__init__.py — реэкспорт моделей платежей.
#
# Импорт моделей из подмодулей для удобства:
#   from apps.payments.models import Payment, PaymentEvent
# вместо:
#   from apps.payments.models.payment import Payment
#   from apps.payments.models.payment_event import PaymentEvent
# ────────────────────────────────────────────────────────────────────────

from apps.payments.models.payment import Payment
from apps.payments.models.payment_event import PaymentEvent

__all__ = ['Payment', 'PaymentEvent']
