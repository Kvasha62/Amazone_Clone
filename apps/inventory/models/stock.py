# ────────────────────────────────────────────────────────────────────────
# apps/inventory/models/stock.py — остатки варианта товара на складе.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • OneToOne к ProductVariant — у каждого варианта ровно ОДНА запись Stock
#   • quantity — физическое количество на складе (целое, ≥ 0)
#   • reserved_quantity — зарезервировано под заказы (≤ quantity)
#   • available_quantity = quantity - reserved_quantity (computed property)
#   • low_stock_threshold — порог «мало товара» (для уведомлений)
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Два числа: quantity и reserved_quantity»:
#   quantity          — сколько ФИЗИЧЕСКИ лежит на полке
#   reserved_quantity — сколько из них уже ЗАБРОНИРОВАНО под заказы
#   available         = quantity - reserved — сколько ЕЩЁ МОЖНО продать
#
#   Пример:
#     quantity = 100 шт. (на полке)
#     reserved = 30 шт. (подтверждённые заказы, ещё не отгружены)
#     available = 70 шт. (можно добавить в корзину)
#
#   Зачем два числа:
#     Без reserved_quantity → при отмене заказа мы не знаем,
#     сколько «вернуть» на полку — мы не знаем, было ли списание.
#     С reserved → отмена = release = reserved -= X, quantity не меняется.
#
# 📖 https://en.wikipedia.org/wiki/Inventory_management
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
# 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Таблица inventory_stock не создастся → CartService не сможет проверять остатки
#   • ProductVariant.variant.stock → RelatedObjectDoesNotExist
# ────────────────────────────────────────────────────────────────────────

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.inventory.constants import LOW_STOCK_THRESHOLD
from apps.inventory.managers.stock_manager import StockManager


class Stock(BaseModel):
    """
    Остатки варианта товара на складе.

    OneToOne → у каждого ProductVariant ровно ОДНА запись Stock.
    Связь обратная: variant.stock → доступ к остаткам.

    КЛЮЧЕВЫЕ ПОЛЯ:
      quantity           — физический остаток (штук на полке)
      reserved_quantity  — зарезервировано под заказы
      available_quantity — property: quantity - reserved_quantity

    📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
    """

    # variant — OneToOne к ProductVariant.
    # on_delete=CASCADE — при удалении варианта удаляем остатки.
    # related_name='stock' → variant.stock → доступ к Stock.
    # primary_key=False — оставляем авто-PK из BaseModel (id BigAutoField).
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
    variant = models.OneToOneField(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        primary_key=False,
        related_name='stock',
        verbose_name='Вариант товара',
    )

    # quantity — физическое количество на складе.
    # PositiveIntegerField → CHECK (quantity >= 0) в PostgreSQL.
    # MinValueValidator(0) — дублирует на уровне Python.
    # default=0 — новый вариант → 0 штук (пока не приёмка).
    # db_index=True — частый фильтр: Stock.objects.filter(quantity__gt=0)
    quantity = models.PositiveIntegerField(
        verbose_name='Количество на складе',
        default=0,
        db_index=True,
        validators=[MinValueValidator(0)],
    )

    # reserved_quantity — сколько из quantity забронировано под заказы.
    # НЕ может быть > quantity (CheckConstraint ниже).
    # default=0 — новый вариант → ничего не зарезервировано.
    reserved_quantity = models.PositiveIntegerField(
        verbose_name='Зарезервировано',
        default=0,
        validators=[MinValueValidator(0)],
    )

    # low_stock_threshold — порог «мало товара».
    # Если quantity ≤ threshold → отправляем уведомление.
    # Задаётся индивидуально для каждого варианта (разные товары — разные нормы).
    low_stock_threshold = models.PositiveIntegerField(
        verbose_name='Порог мало товара',
        default=LOW_STOCK_THRESHOLD,
        validators=[MinValueValidator(0)],
        help_text=(
            'Если количество на складе ≤ этого значения — '
            'отправляется уведомление о необходимости пополнения.'
        ),
    )

    # Пользовательский менеджер с QuerySet-методами.
    objects = StockManager()

    class Meta:
        db_table = 'inventory_stock'
        verbose_name = 'Остаток на складе'
        verbose_name_plural = 'Остатки на складе'
        ordering = ('-created_at',)

        indexes = [
            # Индекс по variant — OneToOne уже создаёт unique index,
            # но явный индекс полезен для covering queries.
            models.Index(
                fields=['variant'],
                name='inventory_stock_variant_idx',
            ),
            # Составной индекс для быстрого поиска «мало товара»:
            # Stock.objects.filter(quantity__lte=F('low_stock_threshold'))
            models.Index(
                fields=['quantity', 'low_stock_threshold'],
                name='inventory_stock_low_qty_idx',
            ),
        ]

        constraints = [
            # ── CheckConstraint: reserved_quantity ≤ quantity ──
            # Зарезервировано не может быть больше чем есть физически.
            # Без: reserved=100, quantity=50 → available=-50 → можно «продать» -50 шт.
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__lte=models.F('quantity')),
                name='stock_reserved_lte_quantity',
            ),
            # ── CheckConstraint: quantity ≥ 0 ──
            # PositiveIntegerField уже гарантирует это, но CheckConstraint
            # защищает при bulk_update и raw SQL.
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name='stock_quantity_non_negative',
            ),
            # ── CheckConstraint: reserved_quantity ≥ 0 ──
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__gte=0),
                name='stock_reserved_non_negative',
            ),
        ]

    def __str__(self):
        """
        «SKU-A: 70 avail / 100 total (30 reserved)»
        """
        return (
            f'{getattr(self.variant, "sku", "???")}: '
            f'{self.available_quantity} avail / '
            f'{self.quantity} total '
            f'({self.reserved_quantity} reserved)'
        )

    # ──────────────────────────────────────────────────────────────
    # Computed properties
    # ──────────────────────────────────────────────────────────────

    @property
    def available_quantity(self) -> int:
        """
        Доступное количество = quantity - reserved_quantity.

        Это количество, которое МОЖНО добавить в корзину / заказать.
        Если available = 0 → вариант показывается как «нет в наличии».

        📖 https://docs.python.org/3/library/functions.html#property
        """
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self) -> bool:
        """
        True если остаток ≤ порога (мало товара).
        Используется в уведомлениях и management command.
        """
        return self.quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self) -> bool:
        """True если физически 0 штук на складе."""
        return self.quantity == 0
