# ────────────────────────────────────────────────────────────────────────
# apps/pricing/constants.py — константы модуля ценообразования.
#
# 📖 https://docs.python.org/3/library/decimal.html
# ┓ ┗─ Почему Decimal, а не float: 0.1 + 0.2 ≠ 0.3 в float.
#      Для денег — только Decimal (точное представление).
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

# Минимальная допустимая цена — 1 копейка (0.01).
# Защита от ошибок ввода: цена = 0 или 0.00001.
# 0.01₽ — минимальная денежная единица в РФ (копейка).
# 📖 https://en.wikipedia.org/wiki/Kopek
MIN_PRICE = Decimal('0.01')

# Максимальная цена — 99 999 999.99₽ (~$1M).
# Защита от опечаток: цена = 999999999999999₽.
# Разумный предел для e-commerce — даже автомобили дешевле.
# _ (underscore) — separator для читаемости (Python 3.6+).
MAX_PRICE = Decimal('99_999_999.99')

# Throttle для pricing API.
# Все pricing-endpoints — только staff (IsAdminUser),
# но throttle защищает от случайных зацикливаний скриптов.
# 📖 https://www.django-rest-framework.org/api-guide/throttling/
PRICING_USER_THROTTLE_RATE = '60/min'
