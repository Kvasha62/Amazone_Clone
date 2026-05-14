from django.db import models
from django.contrib.auth import get_user_model

from apps.catalog.models import ProductVariant


User = get_user_model()


# 🛒 Корзина
class Cart(models.Model):

    # Пользователь (может быть пустым для guest cart)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts'
    )

    # Session key для гостя
    session_key = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    # Дата создания
    created_at = models.DateTimeField(auto_now_add=True)

    # Активна ли корзина
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Cart ({self.user})"

        return f"Guest Cart ({self.session_key})"


# 🧠 Элемент корзины
class CartItem(models.Model):

    # Корзина
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # Вариант товара
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE
    )

    # Количество
    quantity = models.PositiveIntegerField(default=1)

    # Дата добавления
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'variant']

    def __str__(self):
        return f"{self.variant.sku} x {self.quantity}"

    # 💰 Общая стоимость позиции
    @property
    def total_price(self):
        return self.variant.price.price * self.quantity