# ────────────────────────────────────────────────────────────────────────
# apps/cart/models/cart_item.py — позиция (строка) корзины.
#
# БИЗНЕС-СМЫСЛ:
#   CartItem = одна строка в корзине: «iPhone 15 Pro 128GB × 3 шт.»
#   Связывает корзину (Cart) с конкретным вариантом товара (ProductVariant).
#
# ИНВАРИАНТЫ:
#   • Один вариант — одна строка в корзине (UniqueConstraint)
#     Если добавить тот же variant → quantity увеличивается, а не создаётся
#     новая строка.
#   • quantity ∈ [1, 999] (CheckConstraint + serializer validation)
#   • variant on_delete=PROTECT — нельзя удалить вариант, который в корзинах
#
# 📖 Про UniqueConstraint: https://docs.djangoproject.com/en/stable/ref/models/constraints/#uniqueconstraint
# 📖 Про CheckConstraint:  https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
# 📖 Про on_delete:        https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey.on_delete
# 📖 Про Decimal в финансах: https://docs.python.org/3/library/decimal.html#decimal-objects
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Таблица cart_cartitem не создастся → корзина не может содержать товары
#   • Все сервисы и API корзины → ImportError
# ────────────────────────────────────────────────────────────────────────

# Decimal — точный тип для денежных расчётов.
# ПОЧЕМУ НЕ float:
#   float(0.1) + float(0.2) = 0.30000000000000004 (ошибка округления!)
#   Decimal('0.1') + Decimal('0.2') = Decimal('0.3') (точно!)
#   Для цен: 0.01₽ ошибки × 1М транзакций = 10 000₽ потерь.
#   📖 https://docs.python.org/3/library/decimal.html
#   📖 https://0.30000000000000004.com/
from decimal import Decimal

# MinValueValidator — валидатор Django: значение ≥ min_value.
# Используем для quantity ≥ 1.
# 📖 https://docs.djangoproject.com/en/stable/ref/validators/#minvaluevalidator
from django.core.validators import MinValueValidator

# models — ORM Django: поля, связи, индексы.
from django.db import models

# MAX_ITEM_QUANTITY — константа из constants.py (999).
# Вынесена в константы для DRY: используется в CheckConstraint,
# сериализаторах и сервисе.
from apps.cart.constants import MAX_ITEM_QUANTITY

# BaseModel — абстрактная модель с created_at + updated_at.
# 📖 см. apps/core/models/base_model.py
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

    # cart — FK к корзине, которой принадлежит позиция.
    # on_delete=CASCADE — при удалении корзины удаляем все её позиции.
    #   (Корзина удалена → нет смысла хранить её строки.)
    # related_name='items' → cart.items.all() — все позиции корзины.
    #   prefetch_related('items') использует этот related_name.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#foreignkey
    cart = models.ForeignKey(
        'cart.Cart',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина',
    )

    # variant — FK к варианту товара (SKU).
    # on_delete=PROTECT — ЗАПРЕЩАЕТ удаление варианта, если он в корзинах.
    #   Почему не CASCADE: удаление варианта → CartItem исчезнет из корзины
    #   пользователь зайдёт → «где мой товар?» — плохой UX.
    #   PROTECT → заставляет сначала очистить корзины, потом удалять variant.
    # related_name='cart_items' → variant.cart_items.all()
    # Строковая ссылка 'catalog.ProductVariant' — избегаем циклического импорта:
    #   cart.models → catalog.models → (нет обратного импорта) ✅
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#foreignkey
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey.on_delete
    variant = models.ForeignKey(
        'catalog.ProductVariant',           # строка — lazy, избегаем циклов
        on_delete=models.PROTECT,           # PROTECT: вариант не исчезает
        related_name='cart_items',
        verbose_name='Вариант товара',
    )

    # quantity — количество единиц данного варианта.
    # PositiveIntegerField → CHECK (quantity >= 0) на уровне PostgreSQL.
    # Но 0 — невалидно (пустая позиция) → добавляем MinValueValidator(1).
    # default=1 — при создании позиции без указания quantity → 1 штука.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#positiveintegerfield
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        ordering = ('-created_at',)  # новые позиции первыми

        # FK-индексы: Django автоматически создаёт индексы для cart и variant.
        # Не дублируем ( redundant ) — PostgreSQL не использует два одинаковых индекса.

        constraints = [
            # ── UniqueConstraint: один вариант — одна строка в корзине ──
            #
            # fields=['cart', 'variant'] → уникальная пара (cart_id, variant_id).
            # Без: можно добавить SKU-A в корзину #1 два раза →
            #   две строки с разным quantity →CartService.add_item() сломается
            #   (не знает какую строку обновлять).
            #
            # Этот constraint ТАКЖЕ создаёт составной индекс (cart, variant)
            # → ускоряет поиск CartItem.objects.get(cart=X, variant=Y).
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/#uniqueconstraint
            models.UniqueConstraint(
                fields=['cart', 'variant'],
                name='unique_cart_variant',
            ),

            # ── CheckConstraint: quantity ∈ [1, 999] ──
            #
            # Дублирует сериализаторную валидацию, но защищает при:
            #   • bulk_create() — не вызывает clean() / validators
            #   • прямых ORM-вызовах: CartItem.objects.create(quantity=-5)
            #   • management-командах, shell, миграциях
            #
            # Q(quantity__gte=1) — quantity >= 1
            # Q(quantity__lte=MAX_ITEM_QUANTITY) — quantity <= 999
            # & (AND) — оба условия одновременно
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
            models.CheckConstraint(
        condition=(
                    models.Q(quantity__gte=1)
                    & models.Q(quantity__lte=MAX_ITEM_QUANTITY)
                ),
                name='cartitem_quantity_range',
            ),
        ]

    def __str__(self):
        """
        Строковое представление: «SKU-A × 5».

        getattr(self.variant, 'sku', '???') — безопасный доступ к SKU.
        Почему не self.variant.sku:
          • Если variant удалён (PROTECT не даст, но при raw SQL — возможно)
          • Если variant не загружен (N+1 при доступе к __str__ в логах)
          getattr с default '???' → graceful degradation вместо AttributeError.
        """
        sku = getattr(self.variant, 'sku', '???') if self.variant_id else '???'
        return f'{sku} × {self.quantity}'

    # ----------------------------------------------------------
    # Бизнес-логика (computed properties)
    # ----------------------------------------------------------

    @property
    def unit_price(self) -> Decimal | None:
        """
        Цена за единицу товара. None если у варианта нет цены.

        @property — позволяет обращаться как к атрибуту:
          item.unit_price  → Decimal('1500.00')
          item.unit_price  → None (если нет цены)
        Без @property: item.unit_price() → менее элегантно.

        ПОЧЕМУ ВОВЗВРАЩАЕМ None, А НЕ Decimal('0'):
          Товар без цены ≠ бесплатный товар!
          None = «цена неизвестна» → сериализатор покажет null.
          Decimal('0') = «бесплатно» → можно оформить заказ за 0₽ — баг.

        📖 https://docs.python.org/3/library/functions.html#property
        """
        # getattr с default=None — безопасный доступ к связанной цене.
        # variant.price — FK к pricing.PriceVariant (related_name='price').
        # Если FK не установлен → None.
        price_obj = getattr(self.variant, 'price', None)
        if price_obj is None:
            return None
        # price_obj.price — DecimalField на модели цены (pricing app).
        return price_obj.price

    @property
    def total_price(self) -> Decimal | None:
        """
        Стоимость позиции = цена × количество.
        Всегда Decimal или None (если unit_price неизвестна).

        ПРИМЕР:
          unit_price = Decimal('1500.00')
          quantity = 3
          total_price = Decimal('4500.00')

        Decimal × int = Decimal (точное умножение, без float-ошибок).
        📖 https://docs.python.org/3/library/decimal.html#decimal.Decimal.__mul__
        """
        unit = self.unit_price
        if unit is None:
            return None
        # Decimal * int → Decimal (точное умножение)
        return unit * self.quantity
