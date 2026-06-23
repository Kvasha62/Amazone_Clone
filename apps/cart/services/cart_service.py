# ────────────────────────────────────────────────────────────────────────
# apps/cart/services/cart_service.py — бизнес-логика корзины.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Service Layer» (сервисный слой):
#   View → сериализатор (валидация) → сервис (бизнес-логика) → ORM (SQL)
#
#   View НЕ знает про:
#     • transaction.atomic (транзакции)
#     • select_for_update (пессимистичные блокировки)
#     • проверки стока, лимитов, активностей
#     • логику слияния корзин
#   Всё инкапсулировано в сервисе.
#
# БЕЗОПАСНОСТЬ КОНКУРЕНТНОГО ДОСТУПА:
#   Все mutating-методы используют:
#     1. @transaction.atomic — атомарные транзакции
#     2. select_for_update() — пессимистичная блокировка строк
#        PostgreSQL: SELECT ... FOR UPDATE → другие транзакции ждут.
#   Это исключает race conditions:
#     Два параллельных POST /cart/items/ с одинаковым variant_id
#     не создадут две строки (UniqueConstraint + FOR UPDATE).
#
# ⚠️  ВАЖНО: PostgreSQL запрещает FOR UPDATE на nullable-стороне LEFT JOIN.
#   select_for_update() + select_related('variant__stock') → ОШИБКА:
#     "FOR UPDATE не может применяться к NULL-содержащей стороне
#      внешнего соединения"
#   ПРАВИЛО: select_for_update() можно комбинировать ТОЛЬКО с
#   select_related на обязательные FK (INNER JOIN).
#   Обратные OneToOne (stock, price) → LEFT OUTER JOIN →
#   читаем ОТДЕЛЬНЫМ запросом без FOR UPDATE.
#
# 📖 Про Service Layer: https://martinfowler.com/eaaCatalog/serviceLayer.html
# 📖 Про select_for_update: https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
# 📖 Про transaction.atomic: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
# 📖 Про PostgreSQL FOR UPDATE: https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE
# 📖 Про race conditions: https://docs.djangoproject.com/en/stable/topics/db/transactions/#handling-exceptions
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Все API views корзины → ImportError
#   • POST /cart/items/ → 500
#   • GET /cart/ → 500
#   • POST /cart/merge/ → 500
# ────────────────────────────────────────────────────────────────────────

# from __future__ — PEP 604: синтаксис str | None для Python < 3.10.
from __future__ import annotations

import logging

from django.db import transaction

from rest_framework.exceptions import NotFound, ValidationError

from apps.cart.constants import MAX_CART_ITEMS
from apps.cart.models import Cart, CartItem
from apps.catalog.models import ProductVariant

logger = logging.getLogger(__name__)


class CartService:
    """
    Бизнес-логика корзины.

    View не знает про транзакции, select_for_update, проверки стока —
    всё инкапсулировано здесь.

    Все mutating-методы обёрнуты в transaction.atomic и используют
    пессимистичные блокировки (select_for_update), чтобы исключить
    race conditions при параллельных запросах.

    ⚠️  ПРАВИЛО FOR UPDATE + select_related:
      select_for_update() совместим ТОЛЬКО с INNER JOIN
      (обязательные FK). Nullable OneToOne reverse (stock, price)
      дают LEFT OUTER JOIN → PostgreSQL запрещает FOR UPDATE
      на nullable-стороне. Такие связи читаем отдельным запросом.

    📖 https://martinfowler.com/eaaCatalog/serviceLayer.html
    """

    # ----------------------------------------------------------
    # Получение / создание корзины
    # ----------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def get_or_create_cart(request) -> Cart:
        """
        Возвращает активную корзину для текущего запроса.

        ДВА СЦЕНАРИЯ:
          1. Авторизованный: Cart.objects.get_or_create(user=request.user)
          2. Гость: Cart.objects.get_or_create(session_key_hash=hash)
        """
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                is_active=True,
            )
            return cart

        # ── Гость ──
        if not request.session.session_key:
            request.session.create()

        session_hash = Cart.hash_session_key(request.session.session_key)
        cart, _ = Cart.objects.get_or_create(
            session_key_hash=session_hash,
            is_active=True,
        )
        return cart

    # ----------------------------------------------------------
    # Операции над позициями
    # ----------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def add_item(cart: Cart, variant_id: int, quantity: int) -> CartItem:
        """
        Добавляет вариант в корзину или увеличивает количество.

        АЛГОРИТМ (6 шагов):
          0. Базовая валидация quantity
          1. Проверка лимита позиций
          2. Загрузка варианта с проверкой активности
          3. Проверка активности товара
          4. select_for_update — блокировка существующей строки
          5. Проверка остатков на складе
          6. Создание / обновление CartItem
        """
        # ── Шаг 0: Базовая валидация quantity ──
        if quantity < 1:
            raise ValidationError({
                'quantity': 'Количество должно быть не менее 1.',
            })

        # ── Шаг 1: Проверка лимита позиций ──
        existing_count = cart.items.count()
        if existing_count >= MAX_CART_ITEMS:
            raise ValidationError({
                'detail': (
                    f'Максимум позиций в корзине — {MAX_CART_ITEMS}.'
                ),
            })

        # ── Шаг 2: Загрузка варианта с проверкой активности ──
        # select_related('product') — INNER JOIN (обязательный FK) ✅
        # НЕ добавляем 'stock': stock — OneToOne reverse →
        # LEFT OUTER JOIN. Здесь нет select_for_update, поэтому
        # LEFT JOIN допустим. Stock загружаем отдельным запросом ниже.
        try:
            variant = (
                ProductVariant.objects
                .select_related('product')
                .get(pk=variant_id, is_active=True)
            )
        except ProductVariant.DoesNotExist:
            raise NotFound('Вариант товара не найден или неактивен.')

        # ── Шаг 3: Проверка что ТОВАР тоже активен ──
        from apps.catalog.constants import ProductStatus
        if variant.product.status != ProductStatus.ACTIVE:
            raise NotFound('Товар недоступен для заказа.')

        # ── Шаг 4: select_for_update — блокировка строки ──
        # ⚠️  КРИТИЧЕСКОЕ ПРАВИЛО PostgreSQL:
        #   select_for_update() + select_related('variant__stock') →
        #   LEFT OUTER JOIN (stock может быть NULL) →
        #   PostgreSQL: "FOR UPDATE не может применяться к
        #   NULL-содержащей стороне внешнего соединения"
        #
        #   РЕШЕНИЕ: select_related('variant') — только INNER JOIN.
        #   Stock читаем отдельным запросом (шаг 5).
        item = (
            CartItem.objects
            .select_for_update()
            .select_related('variant')  # INNER JOIN — OK с FOR UPDATE
            .filter(cart=cart, variant=variant)
            .first()
        )

        current_qty = item.quantity if item else 0
        new_qty = current_qty + quantity

        # ── Шаг 5: Проверка остатков на складе ──
        # Stock читаем ОТДЕЛЬНЫМ запросом (без select_for_update),
        # потому что OneToOne reverse → LEFT OUTER JOIN →
        # несовместим с FOR UPDATE.
        # Нам нужно только ЧТЕНИЕ stock.quantity — блокировка не нужна.
        # Реальное списание произойдёт при оформлении заказа
        # (OrderService.confirm → InventoryService.reserve).
        stock = (
            ProductVariant.objects
            .filter(pk=variant_id)
            .select_related('stock')
            .values_list('stock__quantity', flat=True)
            .first()
        )
        # stock может быть None (нет записи Stock) или None
        # (stock__quantity = NULL если Stock существует, но quantity NULL —
        #  невозможно т.к. PositiveIntegerField с default=0).
        if stock is not None and new_qty > stock:
            raise ValidationError({
                'quantity': (
                    f'На складе доступно только {stock} шт., '
                    f'в корзине уже {current_qty}.'
                ),
            })

        # ── Шаг 6: Создание / обновление CartItem ──
        if item:
            item.quantity = new_qty
            item.save(update_fields=['quantity', 'updated_at'])
        else:
            item = CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=new_qty,
            )

        logger.info(
            'cart_item_added',
            extra={
                'cart_id': cart.pk,
                'variant_id': variant_id,
                'quantity': new_qty,
            },
        )
        return item

    @staticmethod
    @transaction.atomic
    def update_item_quantity(
        cart: Cart,
        item_id: int,
        quantity: int,
    ) -> CartItem:
        """
        Меняет количество позиции.
        Проверяет сток и блокирует строку до конца транзакции.

        ОТЛИЧИЕ ОТ add_item:
          add_item: quantity ДОБАВЛЯЕТСЯ к текущему (increment)
          update_item_quantity: quantity ЗАМЕНЯЕТ текущее (set)

        ⚠️  Stock читаем ОТДЕЛЬНЫМ запросом (не в select_for_update),
        потому что OneToOne reverse → LEFT OUTER JOIN →
        несовместим с FOR UPDATE.
        """
        # select_for_update() + select_related('variant')
        # INNER JOIN к variant (обязательный FK) → FOR UPDATE работает.
        try:
            item = (
                CartItem.objects
                .select_for_update()
                .select_related('variant')
                .get(pk=item_id, cart=cart)
            )
        except CartItem.DoesNotExist:
            raise NotFound('Позиция корзины не найдена.')

        # Сток читаем отдельным запросом (без select_for_update).
        # LEFT OUTER JOIN без FOR UPDATE — безопасно.
        stock = (
            ProductVariant.objects
            .filter(pk=item.variant_id)
            .select_related('stock')
            .values_list('stock__quantity', flat=True)
            .first()
        )
        if stock is not None and quantity > stock:
            raise ValidationError({
                'quantity': f'На складе доступно только {stock} шт.',
            })

        item.quantity = quantity
        item.save(update_fields=['quantity', 'updated_at'])

        logger.info(
            'cart_item_updated',
            extra={
                'cart_id': cart.pk,
                'item_id': item_id,
                'quantity': quantity,
            },
        )
        return item

    @staticmethod
    @transaction.atomic
    def remove_item(cart: Cart, item_id: int) -> None:
        """
        Удаляет позицию из корзины.
        """
        deleted, _ = CartItem.objects.filter(
            pk=item_id,
            cart=cart,
        ).delete()
        if not deleted:
            raise NotFound('Позиция корзины не найдена.')

        logger.info(
            'cart_item_removed',
            extra={'cart_id': cart.pk, 'item_id': item_id},
        )

    @staticmethod
    @transaction.atomic
    def clear(cart: Cart) -> None:
        """
        Полностью очищает корзину (удаляет все CartItem).
        """
        cart.items.all().delete()
        logger.info('cart_cleared', extra={'cart_id': cart.pk})

    # ----------------------------------------------------------
    # Слияние гостевой корзины в пользовательскую (при логине)
    # ----------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def merge_guest_into_user_cart(session_key: str, user) -> Cart | None:
        """
        При логине переносит позиции из гостевой корзины
        в корзину пользователя.

        АЛГОРИТМ:
          1. Найти гостевую корзину по session_key_hash
          2. Получить/создать корзину пользователя
          3. Для каждой позиции гостевой корзины:
             a. Проверить variant.is_active → пропустить неактивные
             b. Проверить product.status == ACTIVE → пропустить недоступные
             c. Если позиция уже есть в юзерской → сложить quantity
             d. Иначе → создать новую позицию
             e. Ограничить quantity доступным остатком (stock)
             f. Проверить лимит позиций (MAX_CART_ITEMS)
          4. Деактивировать гостевую корзину
        """
        session_hash = Cart.hash_session_key(session_key)

        # select_for_update() — блокируем гостевую корзину.
        guest_cart = (
            Cart.objects
            .select_for_update()
            .filter(session_key_hash=session_hash, is_active=True)
            .first()
        )
        if not guest_cart:
            logger.debug('cart_merge_skip: no guest cart')
            return None

        # select_for_update() — блокируем юзерскую корзину.
        user_cart, _ = (
            Cart.objects
            .select_for_update()
            .get_or_create(user=user, is_active=True)
        )

        # ⚠️  Загружаем позиции гостевой корзины БЕЗ select_for_update.
        # select_related('variant', 'variant__stock') → LEFT OUTER JOIN
        # для stock — допустимо, т.к. здесь НЕТ select_for_update().
        # Stock нужен только для ЧТЕНИЯ (проверка остатков).
        guest_items = (
            guest_cart.items
            .select_related('variant', 'variant__product', 'variant__stock')
            .all()
        )

        from apps.catalog.constants import ProductStatus

        merged_count = 0
        for guest_item in guest_items:
            if not guest_item.variant.is_active:
                logger.debug(
                    'cart_merge_skip_variant_inactive',
                    extra={'variant_id': guest_item.variant_id},
                )
                continue

            if guest_item.variant.product.status != ProductStatus.ACTIVE:
                logger.debug(
                    'cart_merge_skip_product_unavailable',
                    extra={'product_id': guest_item.variant.product_id},
                )
                continue

            # Ищем позицию в юзерской корзине — select_for_update,
            # но БЕЗ select_related на nullable FK.
            existing = (
                CartItem.objects
                .select_for_update()
                .filter(cart=user_cart, variant=guest_item.variant)
                .first()
            )

            target_qty = (
                (existing.quantity if existing else 0) + guest_item.quantity
            )

            # Stock загружен через select_related (без FOR UPDATE) — ок.
            stock = getattr(guest_item.variant, 'stock', None)
            if stock is not None:
                target_qty = min(target_qty, stock.quantity)

            if target_qty <= 0:
                continue

            if not existing:
                current_count = user_cart.items.count()
                if current_count >= MAX_CART_ITEMS:
                    logger.warning(
                        'cart_merge_limit_reached',
                        extra={
                            'user_id': user.pk,
                            'variant_id': guest_item.variant_id,
                        },
                    )
                    continue

            if existing:
                existing.quantity = target_qty
                existing.save(update_fields=['quantity', 'updated_at'])
            else:
                CartItem.objects.create(
                    cart=user_cart,
                    variant=guest_item.variant,
                    quantity=target_qty,
                )

            merged_count += 1

        # Деактивируем гостевую корзину (не удаляем!).
        guest_cart.is_active = False
        guest_cart.save(update_fields=['is_active', 'updated_at'])

        logger.info(
            'cart_merged',
            extra={
                'user_id': user.pk,
                'merged_count': merged_count,
            },
        )
        return user_cart
