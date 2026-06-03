# from django.db import models
# from django.contrib.auth import get_user_model
#
# from apps.catalog.models import ProductVariant
#
#
# User = get_user_model()
#
#
# # 🛒 Корзина
# class Cart(models.Model):
#
#     # Пользователь (может быть пустым для guest cart)
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name='carts',
#         verbose_name='Корзина'
#     )
#
#     # Session key для гостя
#     session_key = models.CharField(
#         max_length=255,
#         null=True,
#         blank=True
#     )
#
#     # Дата создания
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     # Активна ли корзина
#     is_active = models.BooleanField(default=True)
#
#     class Meta:
#         ordering = ['-created_at']
#
#     def __str__(self):
#         if self.user:
#             return f"Cart ({self.user})"
#
#         return f"Guest Cart ({self.session_key})"
#
#
# # 🧠 Элемент корзины
# class CartItem(models.Model):
#
#     # Корзина
#     cart = models.ForeignKey(
#         Cart,
#         on_delete=models.CASCADE,
#         related_name='items',
#         verbose_name='Продукты'
#     )
#
#     # Вариант товара
#     variant = models.ForeignKey(
#         ProductVariant,
#         on_delete=models.CASCADE
#     )
#
#     # Количество
#     quantity = models.PositiveIntegerField(default=1)
#
#     # Дата добавления
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         unique_together = ['cart', 'variant']
#
#     def __str__(self):
#         return f"{self.variant.sku} x {self.quantity}"
#
#     # 💰 Общая стоимость позиции
#     @property
#     def total_price(self):
#         return self.variant.price.price * self.quantity

from django.db import models
from django.contrib.auth import get_user_model

from apps.catalog.models import ProductVariant

User = get_user_model()


class Cart(models.Model):
    """
    Корзина пользователя.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name='Пользователь'
    )

    session_key = models.CharField(
        'Ключ сессии',
        max_length=255,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )

    is_active = models.BooleanField(
        'Активна',
        default=True
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f'Корзина ({self.user})'

        return f'Гостевая корзина ({self.session_key})'


class CartItem(models.Model):
    """
    Элемент корзины.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина'
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        verbose_name='Вариант товара'
    )

    quantity = models.PositiveIntegerField(
        'Количество',
        default=1
    )

    created_at = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ['cart', 'variant']

    def __str__(self):
        return f'{self.variant.sku} × {self.quantity}'

    @property
    def total_price(self):
        return self.variant.price.price * self.quantity