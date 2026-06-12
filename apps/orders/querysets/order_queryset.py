# ────────────────────────────────────────────────────────────────────────
# apps/orders/querysets/order_queryset.py — кастомный QuerySet для Order.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Fat QuerySet, Thin View»:
#   Повторяющиеся запросы выносятся в методы QuerySet → DRY.
#   View/сервис вызывает Order.objects.for_user(user) вместо
#   написания .filter(user=user, ...).select_related(...).prefetch_related(...)
#
# ПОЧЕМУ from_queryset(), А НЕ ПРОСТО MANAGER-МЕТОДЫ:
#   from_queryset() «подмешивает» методы QuerySet в Manager:
#     Order.objects.for_user(user)  → работает (из QuerySet)
#     Order.objects.all().for_user(user)  → тоже работает (chaining)
#   Если бы методы были в Manager — chaining бы сломался.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Order.objects.with_items() → AttributeError
#   • Order.objects.for_user() → AttributeError
#   • API views → 500 при попытке получить список заказов
# ────────────────────────────────────────────────────────────────────────

from django.db import models


class OrderQuerySet(models.QuerySet):
    """
    Кастомный QuerySet с методами для частых запросов к заказам.

    Используется через OrderManager.from_queryset(OrderQuerySet).
    Все методы возвращают QuerySet → chaining:
        Order.objects.for_user(user).pending().with_items()
    """

    # ──────────────────────────────────────────────────────────────
    # Фильтрация по владельцу
    # ──────────────────────────────────────────────────────────────
    def for_user(self, user):
        """
        Фильтрует заказы по пользователю.

        ПРИМЕР:
          Order.objects.for_user(request.user)

        ЗАЩИТА:
          Гарантирует что пользователь видит ТОЛЬКО свои заказы.
          View не фильтрует вручную → меньше шансов на ошибку (IDOR).
          📖 https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
        """
        return self.filter(user=user)

    # ──────────────────────────────────────────────────────────────
    # Фильтрация по статусу
    # ──────────────────────────────────────────────────────────────
    def pending(self):
        """
        Заказы в статусе PENDING (ожидают оплаты).
        Используется в cleanup_stale_orders и при оплате.
        """
        from apps.orders.models.order import OrderStatus
        return self.filter(status=OrderStatus.PENDING)

    def active(self):
        """
        «Активные» заказы — все, кроме терминальных (DELIVERED, CANCELLED).
        Используется в списке «Мои текущие заказы».
        """
        from apps.orders.models.order import OrderStatus
        return self.exclude(
            status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED],
        )

    def cancelled(self):
        """Отменённые заказы — для аналитики и отчётов."""
        from apps.orders.models.order import OrderStatus
        return self.filter(status=OrderStatus.CANCELLED)

    # ──────────────────────────────────────────────────────────────
    # Оптимизация запросов (prefetch / select_related)
    # ──────────────────────────────────────────────────────────────
    def with_items(self):
        """
        Подгружает позиции заказа с variant и ценами за один запрос.

        БЕЗ with_items():
          order = Order.objects.get(pk=1)        → 1 SQL
          for item in order.items.all():         → 1 SQL (N items)
              item.variant                       → 1 SQL per item
              item.variant.product               → 1 SQL per item
          ИТОГО: 1 + N + N + N = 3N + 1 запросов (N = кол-во позиций)

        С with_items():
          prefetch_related('items__variant__product') → 2-3 SQL
          ИТОГО: 2-3 запроса при ЛЮБОМ N!

        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related
        """
        return self.prefetch_related(
            'items',
            'items__variant',
            'items__variant__product',
        )

    def with_user(self):
        """
        Подгружает пользователя (JOIN) — для админки и детального просмотра.
        select_related → INNER JOIN → 1 SQL вместо N+1.
        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related
        """
        return self.select_related('user')
