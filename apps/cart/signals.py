# ────────────────────────────────────────────────────────────────────────
# apps/cart/signals.py — сигнал слияния гостевой корзины при логине.
#
# АРХИТЕКТУРА:
#   Django сигнал user_logged_in срабатывает при session-based авторизации
#   (django.contrib.auth.login()). Функция merge_guest_cart_on_login()
#   переносит позиции из гостевой корзины в корзину пользователя.
#
# ВНИМАНИЕ — ЭТО НЕ РАБОТАЕТ ДЛЯ JWT:
#   JWT-авторизация (SimpleJWT) НЕ вызывает django.contrib.auth.login()
#   → сигнал НЕ срабатывает → корзина НЕ сливается.
#   Для JWT: POST /api/v1/cart/merge/ (CartMergeView).
#
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#django.contrib.auth.signals.user_logged_in
# 📖 https://docs.djangoproject.com/en/stable/topics/signals/
# 📖 https://django-rest-framework-simplejwt.readthedocs.io/en/latest/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • При session-based логине гостевая корзина НЕ сольётся
#   • Пользователь увидит пустую корзину после логина
# ────────────────────────────────────────────────────────────────────────

# logging — для отладки (logger.debug / logger.info).
import logging

# user_logged_in — сигнал Django, посылаемый при успешном логине
# через django.contrib.auth.authenticate() + login().
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#django.contrib.auth.signals.user_logged_in
from django.contrib.auth.signals import user_logged_in

# receiver — декоратор для подключения обработчика к сигналу.
# 📖 https://docs.djangoproject.com/en/stable/topics/signals/#connecting-receiver-functions
from django.dispatch import receiver

# CartService — бизнес-логика слияния корзин.
from apps.cart.services.cart_service import CartService

# Создаём логгер модуля.
logger = logging.getLogger(__name__)


# @receiver(user_logged_in) — регистрирует функцию как обработчик
# сигнала user_logged_in. Каждый раз когда пользователь логинится
# через session-based auth → Django вызывает эту функцию.
#
# АРГУМЕНТЫ сигнала user_logged_in:
#   sender  — класс User (модель пользователя)
#   request — HttpRequest текущего запроса
#   user    — экземпляр User (только что залогиненный)
#   **kwargs — дополнительные аргументы (для совместимости)
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#django.contrib.auth.signals.user_logged_in
@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    """
    При логине через session-авторизацию переносим гостевую корзину
    в пользовательскую.

    АЛГОРИТМ:
      1. Получить session_key из request.session
      2. Вызвать CartService.merge_guest_into_user_cart()
      3. Гостевая корзина деактивируется, позиции переносятся

    ВНИМАНИЕ: этот сигнал НЕ срабатывает при JWT / Token-авторизации.
    Для JWT используйте POST /api/v1/cart/merge/ (CartMergeView).

    📖 https://docs.djangoproject.com/en/stable/ref/signals/#django.contrib.auth.signals.user_logged_in
    """
    # request.session.session_key — текущий ключ сессии.
    # Если session middleware не активен → session_key = None.
    session_key = request.session.session_key
    if not session_key:
        # Нет ключа сессии — нечего сливать.
        # Это нормально при некоторых конфигурациях.
        logger.debug('cart_merge_skip: no session_key at login')
        return

    # Вызываем сервис слияния.
    # merge_guest_into_user_cart() делает:
    #   1. Находит гостевую корзину по session_key_hash
    #   2. Находит/создаёт пользовательскую корзину
    #   3. Переносит позиции (с проверками стока, лимитов)
    #   4. Деактивирует гостевую корзину
    result = CartService.merge_guest_into_user_cart(session_key, user)
    if result:
        # result = Cart (пользовательская корзина) → логируем успех.
        logger.info('cart_merged_on_login', extra={'user_id': user.pk})
