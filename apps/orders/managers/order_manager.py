# ────────────────────────────────────────────────────────────────────────
# apps/orders/managers/order_manager.py — кастомный менеджер для Order.
#
# OrderManager = Manager.from_queryset(OrderQuerySet).
# Это «подмешивает» все методы OrderQuerySet в стандартный Manager.
#
# РЕЗУЛЬТАТ:
#   Order.objects.for_user(user)    → из OrderQuerySet
#   Order.objects.with_items()      → из OrderQuerySet
#   Order.objects.create(...)       → стандартный Manager
#   Order.objects.filter(...)       → стандартный QuerySet
#
# ОБЯЗАТЕЛЬНО: objects = OrderManager() в модели Order.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Order.objects.with_items() → AttributeError
#   • Order.objects.for_user() → AttributeError
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.orders.querysets.order_queryset import OrderQuerySet


class OrderManager(models.Manager.from_queryset(OrderQuerySet)):
    """
    Кастомный менеджер для Order с методами из OrderQuerySet.

    from_queryset(OrderQuerySet) «подмешивает» все методы QuerySet
    в Manager → доступны через Order.objects.<method>().

    📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#creating-a-manager-with-queryset-methods
    """

    # Дополнительные методы менеджера (не QuerySet) можно добавить здесь.
    # Методы менеджера → доступны через Order.objects.method()
    # Методы QuerySet → доступны через Order.objects.all().method() (chaining)
    # Разница: Manager-методы НЕ поддерживают chaining.

    pass
