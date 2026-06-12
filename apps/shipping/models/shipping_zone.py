# ────────────────────────────────────────────────────────────────────────
# apps/shipping/models/shipping_zone.py — зона доставки.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Географическая зона (Москва и МО, Центральная Россия, Дальний Восток)
#   • Каждая зона имеет свои тарифы доставки
#   • Зоны используются для расчёта стоимости доставки
#   • Зона определяется по адресу доставки (город / регион)
#
# АРХИТЕКТУРНЫЕ РЕШЕНИЯ:
#   • zone_code — уникальный код зоны (msk, central, fareast)
#   • regions — JSON-список регионов/городов, входящих в зону
#   • is_active — можно временно отключить зону (сезонность)
#
# ПОЧЕМУ JSON, А НЕ M2M:
#   M2M с таблицей городов → десятки тысяч записей → медленные JOIN'ы.
#   JSON с предзаполненным списком регионов → быстрый lookup.
#   Для SQLite/PostgreSQL JSONField работает отлично.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#jsonfield
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • ShippingMethod не сможет ссылаться на зону (FK)
#   • Расчёт стоимости доставки невозможен
# ────────────────────────────────────────────────────────────────────────

from django.db import models

from apps.core.models.base_model import BaseModel
from apps.shipping.constants import MAX_NAME_LENGTH, MAX_ZONE_CODE_LENGTH


class ShippingZone(BaseModel):
    """
    Географическая зона доставки.

    Определяет регион, для которого действуют определённые тарифы.
    Каждая зона может содержать несколько регионов/городов.

    ПРИМЕРЫ:
      • «Москва и МО» → regions: ["Москва", "Московская область"]
      • «Центральная Россия» → regions: ["Тульская обл.", "Калужская обл.", ...]
      • «Дальний Восток» → regions: ["Хабаровский край", "Приморский край", ...]

    СВЯЗИ:
      • ShippingMethod (reverse FK) — способы доставки в этой зоне
    """

    # Человекочитаемое название зоны
    name = models.CharField(
        verbose_name='Название зоны',
        max_length=MAX_NAME_LENGTH,
    )

    # Уникальный код зоны (используется в API и бизнес-логике)
    zone_code = models.CharField(
        verbose_name='Код зоны',
        max_length=MAX_ZONE_CODE_LENGTH,
        unique=True,
        db_index=True,
        help_text=(
            'Уникальный код зоны: msk, central, fareast. '
            'Используется для программного определения зоны по адресу.'
        ),
    )

    # Список регионов/городов, входящих в зону
    # Хранится как JSON: ["Москва", "Московская область"]
    # Для определения зоны: если city или region в списке → эта зона
    regions = models.JSONField(
        verbose_name='Регионы',
        default=list,
        blank=True,
        help_text=(
            'Список регионов/городов, входящих в зону. '
            'Формат: ["Москва", "Московская область"]. '
            'Используется для определения зоны по адресу доставки.'
        ),
    )

    # Флаг активности зоны
    # Неактивная зона не участвует в расчётах стоимости доставки
    is_active = models.BooleanField(
        verbose_name='Активна',
        default=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Зона доставки'
        verbose_name_plural = 'Зоны доставки'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} ({self.zone_code})'

    def contains_region(self, region_name: str) -> bool:
        """
        Проверяет, входит ли регион в данную зону.

        Case-insensitive сравнение: «москва» == «Москва».
        Используется в ShippingService.calculate_shipping_cost()
        для определения зоны по адресу доставки.

        ARGS:
            region_name: название региона или города

        RETURNS:
            True если регион входит в зону
        """
        if not region_name or not self.regions:
            return False
        region_lower = region_name.lower()
        return any(
            r.lower() == region_lower
            for r in self.regions
        )
