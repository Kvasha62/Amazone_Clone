# ────────────────────────────────────────────────────────────────────────
# apps/shipping/models/shipping_method.py — способ доставки.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Способ доставки: курьер, самовывоз, почта, экспресс
#   • Привязан к зоне доставки (цены зависят от региона)
#   • Имеет базовую стоимость и стоимость за кг
#   • Бесплатная доставка при заказе от определённой суммы
#   • Сроки доставки (мин/макс дни)
#   • Весовые ограничения (макс вес одной посылки)
#
# АРХИТЕКТУРНЫЕ РЕШЕНИЯ:
#   • base_price + price_per_kg → гибкий расчёт стоимости
#   • free_shipping_threshold — порог бесплатной доставки
#   • estimated_days_min/max — «доставка за 2-5 дней»
#
# ФОРМУЛА СТОИМОСТИ:
#   cost = base_price + (weight_kg × price_per_kg)
#   if order_total >= free_shipping_threshold:
#       cost = 0
#   cost = min(cost, max_shipping_cost)
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#decimalfield
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Shipment не сможет ссылаться на способ доставки (FK)
#   • Расчёт стоимости доставки невозможен
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.shipping.constants import (
    MAX_NAME_LENGTH,
    MAX_PICKUP_ADDRESS_LENGTH,
    MAX_SHIPPING_COST,
    SHIPPING_TYPE_CHOICES,
    SHIPPING_TYPE_COURIER,
)
from apps.shipping.managers.shipping_method_manager import ShippingMethodManager


class ShippingMethod(BaseModel):
    """
    Способ доставки в определённой зоне.

    Описывает тарифы и сроки для конкретного типа доставки
    (курьер, самовывоз, почта, экспресс) в конкретной зоне.

    ПРИМЕР:
      • Курьерская доставка в Москве и МО:
        base_price=300, price_per_kg=50, estimated_days_min=1, max=2
      • Экспресс-доставка в Москве:
        base_price=800, price_per_kg=100, estimated_days_min=0, max=1
      • Почта России по всей стране:
        base_price=250, price_per_kg=30, estimated_days_min=7, max=30

    СВЯЗИ:
      • ShippingZone (FK) — зона, к которой привязан способ
      • Shipment (reverse FK) — отправления данным способом
    """

    objects = ShippingMethodManager()

    # ── Название способа доставки ──
    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_NAME_LENGTH,
        help_text='Например: «Курьерская доставка (Москва)»',
    )

    # ── Тип доставки ──
    shipping_type = models.CharField(
        verbose_name='Тип доставки',
        max_length=20,
        choices=SHIPPING_TYPE_CHOICES,
        default=SHIPPING_TYPE_COURIER,
        db_index=True,
    )

    # ── Зона доставки ──
    zone = models.ForeignKey(
        'shipping.ShippingZone',
        on_delete=models.PROTECT,
        related_name='methods',
        verbose_name='Зона доставки',
    )

    # ── Базовая стоимость (фиксированная часть) ──
    # Это стоимость доставки «пустой коробки».
    # К ней прибавляется price_per_kg × вес заказа.
    base_price = models.DecimalField(
        verbose_name='Базовая стоимость (₽)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Фиксированная часть стоимости доставки.',
    )

    # ── Стоимость за 1 кг ──
    # Умножается на вес заказа (кг) и прибавляется к base_price.
    # 0 = доставка не зависит от веса (единый тариф).
    price_per_kg = models.DecimalField(
        verbose_name='Стоимость за 1 кг (₽)',
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Добавочная стоимость за каждый кг веса.',
    )

    # ── Порог бесплатной доставки ──
    # Если сумма заказа ≥ порога → стоимость доставки = 0.
    # null = бесплатная доставка недоступна при любой сумме.
    free_shipping_threshold = models.DecimalField(
        verbose_name='Бесплатная доставка от (₽)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            'Если сумма заказа ≥ этого значения — доставка бесплатная. '
            'Пусто = всегда платная.'
        ),
    )

    # ── Максимальная стоимость доставки ──
    # Стоимость не может превышать это значение (cap).
    # null = без ограничений (cap не применяется).
    max_shipping_cost = models.DecimalField(
        verbose_name='Макс. стоимость доставки (₽)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Верхний предел стоимости доставки. Пусто = без ограничений.',
    )

    # ── Сроки доставки (дни) ──
    estimated_days_min = models.PositiveSmallIntegerField(
        verbose_name='Мин. срок доставки (дни)',
        default=1,
        help_text='Минимальное количество дней для доставки.',
    )
    estimated_days_max = models.PositiveSmallIntegerField(
        verbose_name='Макс. срок доставки (дни)',
        default=7,
        help_text='Максимальное количество дней для доставки.',
    )

    # ── Весовые ограничения ──
    max_weight_kg = models.DecimalField(
        verbose_name='Макс. вес (кг)',
        max_digits=8,
        decimal_places=3,
        default=Decimal('30.000'),
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Максимальный вес одной посылки (кг).',
    )

    # ── Адрес пункта выдачи (для PICKUP) ──
    # Заполняется только для типа PICKUP.
    # Для COURIER / EXPRESS адрес = адрес клиента (в Order).
    # Для POST адрес = почтовое отделение.
    pickup_address = models.TextField(
        verbose_name='Адрес пункта выдачи',
        blank=True,
        default='',
        max_length=MAX_PICKUP_ADDRESS_LENGTH,
        help_text='Заполняется только для самовывоза.',
    )

    # ── Флаг активности ──
    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
        db_index=True,
    )

    # ── Приоритет сортировки ──
    # Меньшее значение = показывается выше в списке.
    # Используется в API: курьер (10) → самовывоз (20) → почта (30).
    sort_order = models.PositiveSmallIntegerField(
        verbose_name='Порядок сортировки',
        default=100,
        help_text='Меньшее значение = показывается выше.',
    )

    class Meta:
        verbose_name = 'Способ доставки'
        verbose_name_plural = 'Способы доставки'
        ordering = ('sort_order', 'base_price')
        indexes = [
            models.Index(
                fields=['zone', 'is_active'],
                name='ship_meth_zone_act_idx',
            ),
            models.Index(
                fields=['shipping_type', 'is_active'],
                name='ship_meth_type_act_idx',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_shipping_type_display()})'

    @property
    def estimated_days_display(self) -> str:
        """
        Человекочитаемый срок доставки.

        ПРИМЕРЫ:
          • min=1, max=1 → «1 день»
          • min=2, max=5 → «2-5 дней»
          • min=0, max=1 → «Сегодня-завтра»
        """
        if self.estimated_days_min == 0 and self.estimated_days_max == 0:
            return 'Сегодня'
        if self.estimated_days_min == 0 and self.estimated_days_max == 1:
            return 'Сегодня-завтра'
        if self.estimated_days_min == self.estimated_days_max:
            return f'{self.estimated_days_min} дн.'
        return f'{self.estimated_days_min}-{self.estimated_days_max} дн.'

    def calculate_cost(
        self,
        order_total: Decimal,
        weight_kg: Decimal | None = None,
    ) -> Decimal:
        """
        Рассчитывает стоимость доставки для данного заказа.

        ФОРМУЛА:
          cost = base_price + (price_per_kg × weight_kg)
          if order_total >= free_shipping_threshold → cost = 0
          if max_shipping_cost → cost = min(cost, max_shipping_cost)

        ARGS:
            order_total: сумма заказа (для проверки порога бесплатной доставки)
            weight_kg: вес заказа в кг (если None → считается только base_price)

        RETURNS:
            Стоимость доставки (Decimal, 2 знака)
        """
        # Проверка бесплатной доставки
        if (
            self.free_shipping_threshold is not None
            and order_total >= self.free_shipping_threshold
        ):
            return Decimal('0.00')

        # Базовая стоимость
        cost = self.base_price

        # Добавочная стоимость за вес
        if weight_kg and self.price_per_kg:
            cost += self.price_per_kg * weight_kg

        # Cap: стоимость не превышает max_shipping_cost
        if self.max_shipping_cost is not None:
            cost = min(cost, self.max_shipping_cost)

        return cost.quantize(Decimal('0.01'))
