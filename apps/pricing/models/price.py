# ────────────────────────────────────────────────────────────────────────
# apps/pricing/models/price.py — актуальная цена варианта товара.
#
# АРХИТЕКТУРА:
#   OneToOne к ProductVariant (related_name='price').
#   Другие модули (Cart, Catalog, Orders) обращаются:
#     variant.price.price       → базовая цена (Decimal)
#     variant.price.sale_price  → цена со скидкой (Decimal | None)
#     variant.price.effective_price → цена со скидкой если есть, иначе базовая
#
# ДЕНОРМАЛИЗАЦИЯ:
#   При изменении Price → сигнал пересчитывает Product.min_price / max_price.
#   Это позволяет фильтровать/сортировать товары по цене без JOIN к вариантам.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
# 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#decimalfield
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • CartItem.unit_price → None (товары без цен)
#   • Catalog listing → нельзя фильтровать по цене
#   • Product.min_price/max_price → никогда не обновятся
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

# MinValueValidator — проверяет что Decimal >= min_value.
# 📖 https://docs.djangoproject.com/en/stable/ref/validators/#minvaluevalidator
from django.core.validators import MinValueValidator

from django.db import models

from apps.core.models.base_model import BaseModel
from apps.pricing.constants import MAX_PRICE
from apps.pricing.managers.price_manager import PriceManager


class Price(BaseModel):
    """
    Актуальная цена варианта товара.

    OneToOne → у каждого ProductVariant ровно ОДНА запись Price.
    При изменении — старые значения сохраняются в PriceHistory (через сигнал).

    Поля:
      price       — базовая цена (обязательна, > 0)
      sale_price  — цена со скидкой (опциональна, ≤ price)
      currency    — валюта (по умолчанию RUB)

    📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#decimalfield
    """

    class CurrencyChoices(models.TextChoices):
        """Валюты. RUB по умолчанию — целевая аудитория проекта РФ."""
        RUB = 'RUB', 'Рубли'
        USD = 'USD', 'Доллары'
        EUR = 'EUR', 'Евро'

    # variant — OneToOne к ProductVariant.
    # on_delete=CASCADE — при удалении варианта удаляем цену.
    # primary_key=False — оставляем авто-PK из BaseModel (id BigAutoField).
    #   Альтернатива: primary_key=True → variant_id = PK.
    #   Мы отказались: BaseModel уже даёт id, plus PK=variant_id
    #   ломает generic-паттерн Admin и serializer.
    # related_name='price' → variant.price → доступ к цене.
    # Строковая ссылка 'catalog.ProductVariant' — без прямого импорта (no cycles).
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
    variant = models.OneToOneField(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        primary_key=False,       # оставляем авто-PK из BaseModel
        related_name='price',
        verbose_name='Вариант товара',
    )

    # Кастомный менеджер с QuerySet-методами (for_variant, on_sale, for_product).
    objects = PriceManager()

    # price — базовая (регулярная) цена варианта.
    # max_digits=12, decimal_places=2 → до 99 999 999 999.99
    # MinValueValidator(0.01) — цена не может быть 0 или отрицательной.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#decimalfield
    price = models.DecimalField(
        verbose_name='Цена',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    # sale_price — цена со скидкой. null=True = «без скидки».
    # MinValueValidator(0.01) — скидка не может быть бесплатной.
    # CheckConstraint ниже гарантирует sale_price ≤ price.
    sale_price = models.DecimalField(
        verbose_name='Цена со скидкой',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Цена со скидкой. None = без скидки.',
    )

    currency = models.CharField(
        verbose_name='Валюта',
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.RUB,
    )

    class Meta:
        db_table = 'pricing_price'
        verbose_name = 'Цена'
        verbose_name_plural = 'Цены'
        ordering = ('-created_at',)
        indexes = [
            # Индекс по variant — хотя OneToOne уже создаёт unique index,
            # отдельный Index может быть полезен для covering queries.
            models.Index(
                fields=['variant'],
                name='pricing_price_variant_idx',  # ≤ 30 символов ✅
            ),
        ]
        constraints = [
            # CheckConstraint: price >= 0.01 (защита на уровне БД).
            # Дублирует MinValueValidator — валидатор для форм/API,
            # constraint для bulk / direct SQL.
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
            models.CheckConstraint(
                condition=models.Q(price__gte=Decimal('0.01')),
                name='price_gt_zero',
            ),
            # CheckConstraint: sale_price ≤ price (если sale_price не NULL).
            # Q(sale_price__isnull=True) | Q(sale_price__lte=F('price'))
            # = «sale_price IS NULL OR sale_price <= price»
            # Без: можно установить sale_price=900 при price=100 →
            #   «скидка» увеличивает цену — баг.
            # models.F('price') — ссылка на значение другого поля в той же строке.
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/expressions/#f-expressions
            models.CheckConstraint(
                condition=(
                    models.Q(sale_price__isnull=True)
                    | models.Q(sale_price__lte=models.F('price'))
                ),
                name='sale_price_lte_price',
            ),
        ]

    def __str__(self):
        """
        «1000.00 → 800.00 RUB» (со скидкой)
        «1000.00 RUB» (без скидки)
        """
        if self.sale_price is not None:
            return f'{self.price} → {self.sale_price} {self.currency}'
        return f'{self.price} {self.currency}'

    @property
    def effective_price(self) -> Decimal:
        """
        Эффективная цена: sale_price если есть, иначе базовая price.

        ИСПОЛЬЗОВАНИЕ:
          CartItem.unit_price → variant.price.effective_price
          Cart total → sum(item.effective_price * quantity)

        ПОЧЕМУ НЕ ПРОСТО sale_price or price:
          sale_price может быть Decimal('0.00') (бесплатно).
          `sale_price or price` → 0.00 is falsy → вернёт price — баг!
          Явная проверка `is not None` корректна.
        """
        return self.sale_price if self.sale_price is not None else self.price

    @property
    def discount_percent(self) -> int | None:
        """
        Процент скидки (целое число) или None.

        ФОРМУЛА: (1 - sale_price / price) × 100
        ПРИМЕР: price=1000, sale_price=750 → (1 - 0.75) × 100 = 25%

        Возвращает int (не float) — «25%», а не «25.0%».
        None = нет скидки (sale_price is None).

        📖 https://docs.python.org/3/library/decimal.html#decimal-division
        """
        if self.sale_price is None:
            return None
        # Защита от деления на 0 (price=0 невозможно из-за CheckConstraint,
        # но defensive programming).
        if self.price == 0:
            return 0
        discount = (1 - self.sale_price / self.price) * 100
        return int(discount)
