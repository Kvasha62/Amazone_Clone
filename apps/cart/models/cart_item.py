from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.cart.constants import MAX_ITEM_QUANTITY
from apps.core.models import BaseModel


# ==========================================================
# ЭЛЕМЕНТ КОРЗИНЫ
# ==========================================================

class CartItem(BaseModel):
    """
    Товар (вариант товара) внутри корзины.

    UniqueConstraint(cart, variant) гарантирует, что один и тот же
    вариант не может появиться в корзине дважды — количество всегда
    хранится в одной строке.

    on_delete=PROTECT на variant: при попытке удалить вариант,
    на который есть ссылки в корзинах, БД выбросит ProtectedError.
    Обрабатывайте его на уровне catalog API (Http400 / Http409).
    """

    cart = models.ForeignKey(
        'cart.Cart',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина',
    )

    variant = models.ForeignKey(
        'catalog.ProductVariant',           # строкой — избегаем циклов импорта
        on_delete=models.PROTECT,           # PROTECT: вариант не должен исчезнуть
        related_name='cart_items',          # вместе с записью в корзине
        verbose_name='Вариант товара',
    )

    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        ordering = ('-created_at',)

        # FK-индексы Django создаёт автоматически — не дублируем.
        # UniqueConstraint(cart, variant) уже создаёт индекс на (cart, variant),
        # поэтому отдельный Index не нужен ( redundant ).
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'variant'],
                name='unique_cart_variant',
            ),
            # Проверка диапазона quantity на уровне БД.
            # Дублирует сериализаторную валидацию, но защищает
            # при bulk / прямых ORM-вызовах.
            models.CheckConstraint(
                condition=(
                    models.Q(quantity__gte=1)
                    & models.Q(quantity__lte=MAX_ITEM_QUANTITY)
                ),
                name='cartitem_quantity_range',
            ),
        ]

    def __str__(self):
        # variant может быть не загружен (N+1 риск в логах/debug).
        # В админке используется list_select_related, поэтому там OK.
        sku = getattr(self.variant, 'sku', '???') if self.variant_id else '???'
        return f'{sku} × {self.quantity}'

    # ----------------------------------------------------------
    # Бизнес-логика
    # ----------------------------------------------------------

    @property
    def unit_price(self) -> Decimal | None:
        """
        Цена за единицу. None, если у варианта нет цены.

        Возвращает None, а не Decimal('0.00') — товар без цены
        семантически ≠ «бесплатный». Сериализатор обязан обработать None.
        """
        price_obj = getattr(self.variant, 'price', None)
        if price_obj is None:
            return None
        return price_obj.price

    @property
    def total_price(self) -> Decimal | None:
        """
        Стоимость позиции = цена × количество.
        Всегда Decimal или None (если unit_price неизвестна).
        """
        unit = self.unit_price
        if unit is None:
            return None
        return unit * self.quantity
