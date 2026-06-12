# ────────────────────────────────────────────────────────────────────────
# apps/orders/models/order_item.py — позиция (строка) заказа.
#
# БИЗНЕС-СМЫСЛ:
#   OrderItem = одна строка в заказе: «iPhone 15 Pro 128GB × 3 шт. × 89990₽»
#   Связывает заказ (Order) с конкретным вариантом товара (ProductVariant).
#
# КРИТИЧЕСКОЕ АРХИТЕКТУРНОЕ РЕШЕНИЕ — ЦЕНА КАК SNAPSHOT:
#   unit_price КОПИРУЕТСЯ из Price.effective_price на момент оформления.
#   Это НЕ FK к Price! Если цену товара изменят после оформления заказа —
#   сумма заказа НЕ изменится.
#
#   ПОЧЕМУ ЭТО ВАЖНО:
#     1) Юридическая корректность: чек на 5000₽ должен показывать 5000₽
#        даже если через месяц цена выросла до 7000₽
#     2) Возвраты: если товар стоил 5000₽ → вернуть нужно 5000₽,
#        а не текущую цену (которая могла вырасти или упасть)
#     3) Аналитика: «какая была средняя цена товара X в марте?»
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#decimalfield
# 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Таблица orders_orderitem не создастся → заказ не может содержать товары
#   • Все сервисы и API заказов → ImportError
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.orders.constants import MAX_ITEM_QUANTITY


class OrderItem(BaseModel):
    """
    Позиция заказа — товар с зафиксированной ценой.

    Цена (unit_price) — SNAPSHOT на момент оформления.
    Количество (quantity) — количество единиц.
    product_name / sku — SNAPSHOT названий на момент оформления.

    ПОЧЕМУ КОПИРУЕМ product_name и sku:
      Если товар/вариант будут удалены или переименованы —
      заказ всё равно покажет корректные данные.
      variant может быть NULL (on_delete=SET_NULL) —
      а product_name сохраняется вечно.
    """

    # ──────────────────────────────────────────────────────────────
    # Заказ, которому принадлежит позиция
    # ──────────────────────────────────────────────────────────────
    # on_delete=CASCADE — при удалении заказа удаляем все позиции.
    #   (Заказ удалён → нет смысла хранить его строки.)
    # related_name='items' → order.items.all() — все позиции заказа.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#foreignkey
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )

    # ──────────────────────────────────────────────────────────────
    # Ссылка на вариант товара
    # ──────────────────────────────────────────────────────────────
    # on_delete=SET_NULL — при удалении варианта позиция остаётся!
    #   Почему не CASCADE: удаление варианта ≠ удаление строки заказа.
    #   Заказ — финансовый документ, позиции нельзя «испарить».
    #   SET_NULL + product_name/sku → заказ сохраняет читаемость
    #   даже без живого варианта.
    #
    # null=True — вариант может быть удалён (variant_id = NULL).
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey.on_delete
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Вариант товара',
    )

    # ──────────────────────────────────────────────────────────────
    # SNAPSHOT данных товара (копии на момент оформления)
    # ──────────────────────────────────────────────────────────────
    # product_name — название товара на момент покупки.
    # Копируется из variant.product.name.
    # Если variant удалён → product_name остаётся → читаемость заказа.
    product_name = models.CharField(
        verbose_name='Название товара',
        max_length=500,
    )

    # sku — артикул варианта на момент покупки.
    # Копируется из variant.sku.
    sku = models.CharField(
        verbose_name='Артикул (SKU)',
        max_length=100,
    )

    # unit_price — цена за единицу на момент оформления.
    # Копируется из Price.effective_price (вариант может иметь скидку).
    #
    # ЭТО ПОЛЕ — КЛЮЧЕВОЕ для финансовой целостности:
    #   total заказа = Σ(unit_price × quantity) по всем OrderItem.
    #   Если unit_price = 0 → заказ «бесплатный» — баг!
    #   MinValueValidator(Decimal('0.01')) → цена ≥ 1 копейки.
    #
    # 📖 https://docs.python.org/3/library/decimal.html
    unit_price = models.DecimalField(
        verbose_name='Цена за единицу',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    # ──────────────────────────────────────────────────────────────
    # Количество
    # ──────────────────────────────────────────────────────────────
    # PositiveIntegerField → CHECK (quantity >= 0) на уровне PostgreSQL.
    # MinValueValidator(1) → quantity ≥ 1 (позиция с 0 штук — бессмысленна).
    # MAX_ITEM_QUANTITY = 999 — верхний предел.
    #
    # ПОЧЕМУ НЕ ПРОСТО PositiveIntegerField:
    #   PositiveIntegerField допускает 0 → CheckConstraint строже.
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        ordering = ('created_at',)  # позиции в порядке добавления (ASC!)

        indexes = [
            # Индекс по variant — для аналитики:
            # «Сколько раз продали вариант X?»
            # OrderItem.objects.filter(variant=X).count()
            models.Index(
                fields=['variant'],
                name='orderitem_variant_idx',
            ),
        ]

        constraints = [
            # ── UniqueConstraint: уникальная пара (order, sku) ──
            # Один SKU — максимум одна строка в заказе.
            #
            # ПОЧЕМУ НЕ (order, variant):
            #   variant может стать NULL (SET_NULL при удалении).
            #   NULL ≠ NULL в SQL → UniqueConstraint не сработает
            #   для удалённых вариантов → дубликаты!
            #   sku — текстовое поле, никогда не NULL → надёжно.
            #
            # ПОЧЕМУ ЭТО НУЖНО:
            #   Защита от дублирования: если добавить тот же SKU
            #   дважды → IntegrityError → сервис должен обновить quantity.
            models.UniqueConstraint(
                fields=['order', 'sku'],
                name='unique_order_sku',
            ),
            # ── CheckConstraint: quantity ∈ [1, 999] ──
            # Дублирует сериализаторную валидацию, но защищает при:
            #   • bulk_create() — не вызывает clean() / validators
            #   • прямых ORM-вызовов: OrderItem.objects.create(quantity=-5)
            #   • management-командах, shell, миграциях
            models.CheckConstraint(
                condition=(
                    models.Q(quantity__gte=1)
                    & models.Q(quantity__lte=MAX_ITEM_QUANTITY)
                ),
                name='orderitem_quantity_range',
            ),
            # ── CheckConstraint: unit_price ≥ 0.01 ──
            # Защита от «бесплатных» позиций (цена = 0).
            # Бесплатный товар — это скидка 100%, а не цена 0.
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=Decimal('0.01')),
                name='orderitem_unit_price_positive',
            ),
        ]

    def __str__(self):
        """
        «iPhone 15 Pro 128GB (IP15P-128-BLK) × 3 @ 89990.00»

        Показывает: название, артикул, количество, цену за единицу.
        """
        return f'{self.product_name} ({self.sku}) × {self.quantity} @ {self.unit_price}'

    @property
    def total_price(self) -> Decimal:
        """
        Стоимость позиции = цена × количество.

        Decimal × int = Decimal — точное умножение, без float-ошибок.
        📖 https://docs.python.org/3/library/decimal.html#decimal.Decimal.__mul__

        ПРИМЕР:
          unit_price = Decimal('89990.00')
          quantity = 3
          total_price = Decimal('269970.00')

        ЗАЩИТА ОТ None:
          В Django Admin при создании нового заказа через inline-форму
          unit_price и quantity ещё None (несохранённый экземпляр).
          Возвращаем Decimal('0') вместо TypeError.
        """
        if self.unit_price is None or self.quantity is None:
            return Decimal('0')
        return self.unit_price * self.quantity
