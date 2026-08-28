# ────────────────────────────────────────────────────────────────────────
# apps/pricing/services/pricing_service.py — бизнес-логика ценообразования.
#
# МЕТОДЫ:
#   set_price()               — установить/обновить цену варианта
#   get_price()               — получить объект цены
#   get_effective_price()     — получить эффективную цену (Decimal)
#   remove_price()            — удалить цену варианта
#   get_price_history()       — история изменений
#   bulk_set_prices()         — массовое обновление
#
# ARCH-001 (Pricing → Catalog ownership):
#   PricingService НЕ мутирует catalog.Product напрямую.
#   Обновление денормализованных Product.min_price/max_price
#   делегировано каталогу через CatalogService.recalculate_product_prices().
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/
# 📖 https://docs.djangoproject.com/en/stable/ref/models/expressions/#f-expressions
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#values-list
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.catalog.services.catalog_service import CatalogService
from apps.pricing.models import Price, PriceHistory

logger = logging.getLogger(__name__)


class PricingService:
    """
    Сервис для работы с ценами.

    Все mutating-методы обёрнуты в transaction.atomic.
    """

    @staticmethod
    @transaction.atomic
    def set_price(
        variant,
        price: Decimal,
        sale_price: Decimal | None = None,
        changed_by=None,
        reason: str = '',
    ) -> Price:
        """
        Устанавливает или обновляет цену варианта.

        АЛГОРИТМ:
          1. Валидация: price > 0, sale_price ≤ price
          2. get_or_create — найти существующую или создать новую
          3. Если обновление → создать PriceHistory (old → new)
          4. Пересчитать Product.min_price / max_price

        get_or_create — атомарная операция:
          try: get(variant=variant)
          except: create(variant=variant, defaults={...})
        Возвращает (price_obj, created: bool).

        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#get-or-create
        """
        # ── Валидация ──
        if price <= 0:
            raise ValidationError({
                'price': 'Цена должна быть больше нуля.',
            })

        if sale_price is not None and sale_price > price:
            raise ValidationError({
                'sale_price': 'Цена со скидкой не может быть больше базовой.',
            })

        # ── Создание или обновление ──
        # get_or_create: если цена для варианта уже есть → get (created=False)
        # если нет → create с defaults (created=True)
        price_obj, created = Price.objects.get_or_create(
            variant=variant,
            defaults={
                'price': price,
                'sale_price': sale_price,
            },
        )

        if not created:
            # ── Обновление существующей записи ──
            # Сохраняем историю ДО обновления — нам нужны old values.
            PriceHistory.objects.create(
                variant=variant,
                old_price=price_obj.price,          # Текущая (старая) цена
                new_price=price,                     # Новая цена
                old_sale_price=price_obj.sale_price, # Старая скидка
                new_sale_price=sale_price,            # Новая скидка
                changed_by=changed_by,                # Кто изменил
                reason=reason,                        # Почему
            )
            # Обновляем поля цены.
            # update_fields — оптимизация: UPDATE только указанных полей.
            # updated_at — поле BaseModel, включаем обязательно.
            price_obj.price = price
            price_obj.sale_price = sale_price
            price_obj.save(update_fields=['price', 'sale_price', 'updated_at'])

        else:
            # Новая запись — истории нет (старых цен не было).
            logger.info(
                'price_created',
                extra={'variant_id': variant.pk, 'price': str(price)},
            )

        # ── Пересчёт денормализованных цен на товаре ──
        # ARCH-001: `pricing` НЕ мутирует catalog.Product напрямую.
        # Обновление min_price/max_price делегировано каталогу.
        CatalogService.recalculate_product_prices(variant.product)

        return price_obj

    @staticmethod
    def get_price(variant) -> Price | None:
        """
        Возвращает объект цены варианта или None.

        variant.price — OneToOne related manager.
        DoesNotExist → если цена не задана.
        📖 https://docs.djangoproject.com/en/stable/topics/db/queries/#one-to-one-relationships
        """
        try:
            return variant.price
        except Price.DoesNotExist:
            return None

    @staticmethod
    def get_effective_price(variant) -> Decimal | None:
        """
        Возвращает эффективную цену (sale_price если есть, иначе price).
        None если цена не задана.

        ИСПОЛЬЗУЕТСЯ В:
          CartItem.unit_price → цена за единицу
          Cart total → сумма по корзине
        """
        price_obj = PricingService.get_price(variant)
        if price_obj is None:
            return None
        return price_obj.effective_price

    @staticmethod
    @transaction.atomic
    def remove_price(variant) -> None:
        """
        Удаляет цену варианта и пересчитывает товар.

        .filter(variant=variant).delete() — безопасное удаление:
          если цена есть → delete() → deleted=1 → пересчёт
          если цены нет → deleted=0 → noop
        """
        deleted, _ = Price.objects.filter(variant=variant).delete()
        if deleted:
            # ARCH-001: делегируем пересчёт цен каталогу.
            CatalogService.recalculate_product_prices(variant.product)

    @staticmethod
    def get_price_history(variant, limit: int = 50):
        """
        Возвращает историю изменений цены варианта.
        limit=50 — защита от огромных списков (10 лет истории → тысячи записей).
        """
        return (
            PriceHistory.objects
            .filter(variant=variant)
            .order_by('-created_at')[:limit]
        )

    @staticmethod
    @transaction.atomic
    def bulk_set_prices(prices_data: list[dict], changed_by=None) -> list[Price]:
        """
        Массовое обновление цен.

        prices_data: [{'variant_id': int, 'price': Decimal, 'sale_price': ...}, ...]

        @transaction.atomic — либо ВСЕ цены обновляются, либо НИ ОДНА.
        Без: 5 из 10 обновились, 6-й variant_id не найден → частичное обновление.
        """
        from apps.catalog.models import ProductVariant

        results = []
        for item in prices_data:
            try:
                variant = ProductVariant.objects.get(pk=item['variant_id'])
            except ProductVariant.DoesNotExist:
                raise NotFound(
                    f"Вариант {item['variant_id']} не найден."
                )

            price_obj = PricingService.set_price(
                variant=variant,
                price=item['price'],
                sale_price=item.get('sale_price'),
                changed_by=changed_by,
            )
            results.append(price_obj)

        return results
