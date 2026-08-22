# ────────────────────────────────────────────────────────────────────────
# apps/discounts/constants.py
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

# ── Типы скидок ──
DISCOUNT_TYPE_PERCENT = 'percent'
DISCOUNT_TYPE_FIXED = 'fixed'

DISCOUNT_TYPE_CHOICES = (
    (DISCOUNT_TYPE_PERCENT, 'Процент от суммы'),
    (DISCOUNT_TYPE_FIXED, 'Фиксированная сумма'),
)

# ── Лимиты ──
MAX_COUPON_CODE_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 1000
MAX_TIMES_USED = 100000
MIN_ORDER_AMOUNT_FOR_COUPON = Decimal('100.00')

# ── Префикс номера кампании ──
CAMPAIGN_PREFIX = 'CMP'
CAMPAIGN_NUMBER_DIGITS = 6

# Throttling
COUPON_USER_THROTTLE_RATE = '10/min'
