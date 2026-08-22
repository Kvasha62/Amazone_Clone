# ────────────────────────────────────────────────────────────────────────
# apps/orders/tests/factories.py — фабрики для тестов заказов.
#
# Паттерн «Object Mother / Factory» — создание тестовых объектов
# с разумными значениями по умолчанию.
#
# ПОЧЕМУ НЕ factory_boy:
#   factory_boy — отличная библиотека, но добавляет зависимость.
#   Для нашего проекта достаточно простых helper-функций.
#   Каждая функция создаёт ОДИН объект с валидными defaults.
#
# ПОЧЕМУ НЕ fixtures (JSON):
#   Fixtures — статичные, хрупкие, сложно поддерживать.
#   При изменении модели — нужно обновить все fixtures.
#   Фабрики — динамические, всегда создают валидные объекты.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
# 📖 https://martinfowler.com/bliki/ObjectMother.html
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Все тесты заказов → ImportError (не смогут создать объекты)
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.orders.models import Order, OrderItem
from apps.orders.models.order import OrderStatus

User = get_user_model()

# Глобальный счётчик для уникальных имён пользователей.
# Надёжнее чем time.time() — всегда уникальный даже при быстрых вызовах.
_user_counter = 0


def _next_uid():
    """Возвращает уникальный числовой суффикс для email/username."""
    global _user_counter
    _user_counter += 1
    return _user_counter


def create_test_user(**kwargs):
    """
    Создаёт тестового пользователя с разумными defaults.

    ВЫЗОВ:
      user = create_test_user()
      user = create_test_user(email='custom@test.com')

    defaults:
      email — уникальный (counter-based)
      username — из email
      password — 'testpass123' (usable → можно login)
    """
    uid = _next_uid()
    defaults = {
        'email': f'test_{uid}@example.com',
        'username': f'test_{uid}',
        'first_name': 'Тест',
        'last_name': 'Тестов',
    }
    defaults.update(kwargs)
    user = User.objects.create_user(**defaults)
    return user


def create_test_address(user, **kwargs):
    """
    Создаёт тестовый адрес доставки.

    defaults:
      recipient_name — 'Тест Тестов'
      city — 'Москва'
      street — 'ул. Тестовая, д. 1'
      is_default — True
    """
    from apps.users.models import Address
    defaults = {
        'recipient_name': kwargs.pop('recipient_name', 'Тест Тестов'),
        'country': 'Россия',
        'city': 'Москва',
        'street': 'ул. Тестовая, д. 1',
        'postal_code': '123456',
        'is_default': True,
    }
    defaults.update(kwargs)
    return Address.objects.create(user=user, **defaults)


def create_test_order(user, **kwargs):
    """
    Создаёт тестовый заказ с разумными defaults.

    ВЫЗОВ:
      order = create_test_order(user)
      order = create_test_order(user, status=OrderStatus.CONFIRMED)

    defaults:
      status — PENDING
      recipient_name — 'Тест Тестов'
      city — 'Москва'
      street — 'ул. Тестовая, д. 1'
      subtotal — 1000.00
      delivery_cost — 0.00
      discount — 0.00
      total — 1000.00
    """
    defaults = {
        'status': OrderStatus.PENDING,
        'recipient_name': 'Тест Тестов',
        'country': 'Россия',
        'city': 'Москва',
        'street': 'ул. Тестовая, д. 1',
        'postal_code': '123456',
        'subtotal': Decimal('1000.00'),
        'delivery_cost': Decimal('0.00'),
        'discount': Decimal('0.00'),
        'total': Decimal('1000.00'),
    }
    defaults.update(kwargs)
    return Order.objects.create(user=user, **defaults)


def create_test_order_item(order, **kwargs):
    """
    Создаёт тестовую позицию заказа.

    defaults:
      product_name — 'Тестовый товар'
      sku — 'TEST-SKU-001'
      unit_price — 1000.00
      quantity — 1
    """
    defaults = {
        'product_name': 'Тестовый товар',
        'sku': f'TEST-SKU-{order.pk}-{kwargs.get("quantity", 1)}',
        'unit_price': Decimal('1000.00'),
        'quantity': 1,
    }
    defaults.update(kwargs)
    return OrderItem.objects.create(order=order, **defaults)
