# ────────────────────────────────────────────────────────────────────────
# apps/payments/tests/factories.py — фабрики для тестов платежей.
#
# Паттерн «Object Mother / Factory» — создание тестовых объектов
# с разумными значениями по умолчанию.
#
# ЗАВИСИМОСТИ:
#   • apps/orders/tests/factories.py — create_test_user, create_test_order
#   • apps/catalog/tests/factories.py — brand, product, variant_128
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal
import uuid

from apps.payments.constants import DEFAULT_PAYMENT_PROVIDER, PAYMENT_METHOD_CARD
from apps.payments.models import Payment, PaymentEvent


def create_test_payment(order, user, **kwargs):
    """
    Создаёт тестовый платёж с разумными defaults.

    defaults:
      amount — order.total (или 1000.00 если не указан)
      method — 'card'
      provider — 'mock'
      external_id — уникальный mock ID
    """
    defaults = {
        'amount': kwargs.pop('amount', getattr(order, 'total', Decimal('1000.00'))),
        'method': PAYMENT_METHOD_CARD,
        'provider': DEFAULT_PAYMENT_PROVIDER,
        'external_id': kwargs.pop('external_id', f'mock_{uuid.uuid4().hex[:16]}'),
    }
    defaults.update(kwargs)
    return Payment.objects.create(order=order, user=user, **defaults)


def create_test_payment_event(payment, **kwargs):
    """
    Создаёт тестовое событие платежа.

    defaults:
      event_type — 'created'
      new_status — 'pending'
    """
    defaults = {
        'event_type': kwargs.pop('event_type', 'created'),
        'new_status': kwargs.pop('new_status', 'pending'),
    }
    defaults.update(kwargs)
    return PaymentEvent.objects.create(payment=payment, **defaults)
