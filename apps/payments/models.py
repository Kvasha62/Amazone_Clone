from django.db import models

from apps.orders.models import Order


class Payment(models.Model):
    """
    Платеж по заказу.

    Сейчас используется Fake Payment.
    В будущем можно подключить ЮKassa,
    Т-Банк, Robokassa и т.д.
    """

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает оплаты'),
        (STATUS_PAID, 'Оплачен'),
        (STATUS_FAILED, 'Ошибка оплаты'),
        (STATUS_REFUNDED, 'Возврат средств'),
    ]

    # Связь с заказом
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name='Заказ'
    )

    # Сумма платежа
    amount = models.DecimalField(
        verbose_name='Сумма',
        max_digits=12,
        decimal_places=2
    )

    # Валюта
    currency = models.CharField(
        verbose_name='Валюта',
        max_length=10,
        default='USD'
    )

    # Внешний идентификатор платежа
    provider_payment_id = models.CharField(
        verbose_name='ID платежа у провайдера',
        max_length=255,
        blank=True,
        null=True
    )

    # Статус платежа
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    # Когда платеж создан
    created_at = models.DateTimeField(
        verbose_name='Создан',
        auto_now_add=True
    )

    # Когда платеж обновлен
    updated_at = models.DateTimeField(
        verbose_name='Обновлен',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'Платеж #{self.id} ({self.status})'