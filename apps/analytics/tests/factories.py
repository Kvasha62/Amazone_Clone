# ────────────────────────────────────────────────────────────────────────
# apps/analytics/tests/factories.py — тестовые фабрики для аналитики.
#
# Хелпер-функции для создания тестовых данных.
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal
from datetime import timedelta

from django.utils import timezone

from apps.analytics.models import ProductView
from apps.orders.models import Order, OrderItem
from apps.orders.models.order import OrderStatus


def create_test_view(
    product,
    *,
    user=None,
    session_key='',
    source='direct',
    created_at=None,
):
    """Создаёт тестовый просмотр товара."""
    view = ProductView.objects.create(
        product=product,
        user=user,
        session_key=session_key,
        source=source,
    )
    if created_at:
        # Переопределяем created_at (для тестов временных рядов)
        ProductView.objects.filter(pk=view.pk).update(created_at=created_at)
        view.refresh_from_db()
    return view


def create_test_delivered_order_with_items(
    user,
    variant,
    *,
    quantity=2,
    unit_price=Decimal('1000.00'),
    days_ago=0,
):
    """
    Создаёт доставленный заказ с позициями (для тестов аналитики).

    ARGS:
        user: покупатель
        variant: вариант товара
        quantity: количество
        unit_price: цена за единицу
        days_ago: сколько дней назад создан заказ

    RETURNS:
        Order (с созданными OrderItem)
    """
    created_at = timezone.now() - timedelta(days=days_ago)

    order = Order.objects.create(
        user=user,
        status=OrderStatus.DELIVERED,
        recipient_name='Тест Тестов',
        country='Россия',
        city='Москва',
        street='ул. Тестовая, д. 1',
        postal_code='123456',
        subtotal=unit_price * quantity,
        delivery_cost=Decimal('0.00'),
        discount=Decimal('0.00'),
        total=unit_price * quantity,
    )

    OrderItem.objects.create(
        order=order,
        variant=variant,
        product_name=variant.product.name,
        sku=variant.sku,
        unit_price=unit_price,
        quantity=quantity,
    )

    # Переопределяем created_at
    Order.objects.filter(pk=order.pk).update(created_at=created_at)
    order.refresh_from_db()

    return order
