# ────────────────────────────────────────────────────────────────────────
# apps/pricing/models/price_history.py — история изменений цен.
#
# БИЗНЕС-ЗНАЧЕНИЕ:
#   • Аудит: кто, когда и почему изменил цену
#   • Аналитика: динамика цен, средняя скидка, частота изменений
#   • Отчёты: «товар подорожал на 15% за последний месяц»
#
# КАК ЗАПОЛНЯЕТСЯ:
#   PricingService.set_price() создаёт PriceHistory перед обновлением Price.
#   НЕ через сигнал (нужно old_price/old_sale_price — а сигнал даёт только new).
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#foreignkey
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#decimalfield
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • История изменений цен потеряна
#   • PricingService.set_price() → ImportError
# ────────────────────────────────────────────────────────────────────────

from decimal import Decimal

from django.db import models

from apps.core.models.base_model import BaseModel


class PriceHistory(BaseModel):
    """
    Запись об изменении цены варианта.

    Создаётся в PricingService.set_price() при ОБНОВЛЕНИИ цены
    (не при первом создании — старых значений нет).

    ПОЛЯ:
      old_price / new_price         — базовая цена (до / после)
      old_sale_price / new_sale_price — цена со скидкой (до / после)
      changed_by                    — кто изменил (FK к User, nullable)
      reason                        — причина изменения (текст)
    """

    # variant — FK к ProductVariant (не OneToOne — у варианта много записей).
    # on_delete=CASCADE — при удалении варианта удаляем всю его историю.
    # related_name='price_history' → variant.price_history.all()
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='Вариант товара',
    )

    # old_price — предыдущая базовая цена. null=True — для первой записи
    # (хотя на практике PricingService не создаёт историю при первом set_price).
    old_price = models.DecimalField(
        verbose_name='Старая цена',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # new_price — новая базовая цена (обязательна).
    new_price = models.DecimalField(
        verbose_name='Новая цена',
        max_digits=12,
        decimal_places=2,
    )

    old_sale_price = models.DecimalField(
        verbose_name='Старая цена со скидкой',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    new_sale_price = models.DecimalField(
        verbose_name='Новая цена со скидкой',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # changed_by — кто изменил цену (для аудита).
    # on_delete=SET_NULL — при удалении пользователя история сохраняется
    #   (changed_by = NULL). CASCADE удалил бы всю историю — потеря данных.
    # null=True, blank=True — может быть None (изменение через management command).
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Кто изменил',
    )

    # reason — причина изменения (например «Сезонная распродажа», «Конкурентная цена»).
    reason = models.CharField(
        verbose_name='Причина',
        max_length=255,
        blank=True,
        default='',
    )

    class Meta:
        db_table = 'pricing_price_history'
        verbose_name = 'История цены'
        verbose_name_plural = 'История цен'
        ordering = ('-created_at',)
        indexes = [
            # Составной индекс (variant, -created_at) — ускоряет:
            #   PriceHistory.objects.filter(variant=X).order_by('-created_at')
            # DESC-индекс: PostgreSQL поддерживает ORDER BY variant ASC, created_at DESC.
            # Имя ≤ 30 символов: pricing_hst_var_cr_idx = 23 ✅
            # 📖 https://www.postgresql.org/docs/current/indexes-ordering.html
            models.Index(
                fields=['variant', '-created_at'],
                name='pricing_hst_var_cr_idx',
            ),
        ]

    def __str__(self):
        """«SKU-P1: 100.00 → 90.00»."""
        return f'{self.variant}: {self.old_price} → {self.new_price}'
