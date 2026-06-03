# from django.db import models
# from django.contrib.auth import get_user_model
#
# from apps.catalog.models import ProductVariant
#
#
# User = get_user_model()
#
#
# # 📦 Заказ
# class Order(models.Model):
#
#     STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('paid', 'Paid'),
#         ('shipped', 'Shipped'),
#         ('completed', 'Completed'),
#         ('cancelled', 'Cancelled'),
#     ]
#
#     # Пользователь
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name='orders'
#     )
#
#     # Статус заказа
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='pending'
#     )
#
#     # Общая сумма
#     total_price = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         default=0
#     )
#
#     # Адрес доставки
#     shipping_address = models.TextField()
#
#     # Дата создания
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         ordering = ['-created_at']
#
#     def __str__(self):
#         return f"Order #{self.id}"
#
#     # 🔥 Пересчет общей суммы
#     def calculate_total(self):
#
#         total = sum(
#             item.total_price for item in self.items.all()
#         )
#
#         self.total_price = total
#
#         self.save()
#
#
# # 📦 Элемент заказа
# class OrderItem(models.Model):
#
#     # Заказ
#     order = models.ForeignKey(
#         Order,
#         on_delete=models.CASCADE,
#         related_name='items'
#     )
#
#     # Вариант товара
#     variant = models.ForeignKey(
#         ProductVariant,
#         on_delete=models.CASCADE
#     )
#
#     # Цена НА МОМЕНТ ПОКУПКИ
#     price = models.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )
#
#     # Количество
#     quantity = models.PositiveIntegerField(default=1)
#
#     class Meta:
#         unique_together = ['order', 'variant']
#
#     def __str__(self):
#         return f"{self.variant.sku} x {self.quantity}"
#
#     # 💰 Общая цена позиции
#     @property
#     def total_price(self):
#         return self.price * self.quantity

from django.db import models
from django.contrib.auth import get_user_model

from apps.catalog.models import ProductVariant

User = get_user_model()


class Order(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь'
    )

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    total_price = models.DecimalField(
        'Общая сумма',
        max_digits=12,
        decimal_places=2,
        default=0
    )

    shipping_address = models.TextField(
        'Адрес доставки'
    )

    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ №{self.id}'

    def calculate_total(self):
        total = sum(
            item.total_price
            for item in self.items.all()
        )

        self.total_price = total
        self.save()


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        verbose_name='Вариант товара'
    )

    price = models.DecimalField(
        'Цена на момент покупки',
        max_digits=10,
        decimal_places=2
    )

    quantity = models.PositiveIntegerField(
        'Количество',
        default=1
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        unique_together = ['order', 'variant']

    def __str__(self):
        return f'{self.variant.sku} × {self.quantity}'

    @property
    def total_price(self):
        return self.price * self.quantity
