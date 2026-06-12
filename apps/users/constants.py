# ────────────────────────────────────────────────────────────────────────
# apps/users/constants.py — константы модуля пользователей.
#
# Все лимиты и настройки вынесены в один файл для DRY.
# 📖 https://docs.djangoproject.com/en/stable/topics/settings/
# ────────────────────────────────────────────────────────────────────────

# Максимальное количество адресов доставки у одного пользователя.
#
# ПОЧЕМУ ЛИМИТ 10:
#   • Защита от DoS: бот создаёт 10 000 адресов → таблица users_address
#     разрастается → замедляет SELECT для всех.
#   • UX: >10 адресов у обычного пользователя — нереальный сценарий.
#   • Сериализация: 10 адресов × 10 полей = 100 значений — быстро.
#     10 000 адресов → 100 000 значений → медленный JSON.
#
# 📖 https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html
MAX_ADDRESSES_PER_USER = 10

# Минимальная длина пароля.
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/passwords/#module-django.contrib.auth.password_validation
# Django имеет AUTH_PASSWORD_VALIDATORS в settings.py, но мы дублируем
# в сериализаторе для явной валидации ДО попадания в Django validators.
# Почему: Django validators дают generic-ошибку, а наш сериализатор —
# конкретную «Минимум 8 символов» на нужном поле.
MIN_PASSWORD_LENGTH = 8

# ────────────────────────────────────────────────────────────────────────
# Throttling — ограничение частоты запросов
# ────────────────────────────────────────────────────────────────────────

# Анонимные запросы к auth-endpoints (регистрация, login).
# '20/min' — жёстче чем для авторизованных, потому что:
#   • Регистрация = создание записей в БД → дорого
#   • Login = хэширование пароля (bcrypt) → CPU-intensive
#   • 20/min достаточно для человека, но сдерживает брутфорс.
# 📖 https://www.django-rest-framework.org/api-guide/throttling/#anoneratethrottle
USER_AUTH_ANON_THROTTLE_RATE = '20/min'

# Авторизованные запросы к auth-endpoints.
# '60/min' — мягче, но всё равно ограничивает скомпрометированные токены.
# 📖 https://www.django-rest-framework.org/api-guide/throttling/#userratethrottle
USER_AUTH_USER_THROTTLE_RATE = '60/min'
