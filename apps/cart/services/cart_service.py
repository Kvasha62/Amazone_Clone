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

    Исключения: бросаем DRF-исключения (NotFound, ValidationError),
    чтобы view'хи могли прокинуть их в Response без лишних try/except.
    """

    # ----------------------------------------------------------
    # Получение / создание корзины
    # ----------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def get_or_create_cart(request) -> Cart:
        """
        Возвращает активную корзину для текущего запроса.

        Для авторизованного — по user.
        Для гостя — по хэшу session_key.

        NB: request.session.create() создаёт запись в django_session.
        При JWT-авторизации без session middleware это может не работать —
        используйте явный merge-эндпоинт.
        """
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                is_active=True,
            )
            return cart

        # Гость: гарантируем наличие сессии.
        # Это создаёт запись django_session, что может быть избыточно
        # для stateless API-клиентов. Если нужен чисто stateless guest-cart,
        # рассмотрите идентификатор в заголовке / localStorage.
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

        Защищено от:
          - неактивных / несуществующих вариантов (NotFound)
          - превышения остатков на складе (ValidationError)
          - race condition при параллельных запросах (select_for_update)
          - превышения лимита позиций в корзине (ValidationError)
        """
        # 1. Проверка лимита позиций *до* тяжёлых запросов
        existing_count = cart.items.count()
        if existing_count >= MAX_CART_ITEMS:
            raise ValidationError({
                'detail': (
                    f'Максимум позиций в корзине — {MAX_CART_ITEMS}.'
                ),
            })

        # 2. Активный вариант + связанные сток / цена одним запросом
        try:
            variant = (
                ProductVariant.objects
                .select_related('stock', 'price')
                .get(pk=variant_id, is_active=True)
            )
        except ProductVariant.DoesNotExist:
            raise NotFound('Вариант товара не найден или неактивен.')

        # 3. Блокируем потенциально существующую строку CartItem
        #    до конца транзакции — иначе два параллельных POST
        #    прочитают одну и ту же quantity и затрут друг друга.
        item = (
            CartItem.objects
            .select_for_update()
            .filter(cart=cart, variant=variant)
            .first()
        )

        # Если позиции ещё нет — текущий лимит уже учтён в existing_count.
        # Если есть — мы обновляем, а не создаём → лимит не нарушается.
        current_qty = item.quantity if item else 0
        new_qty = current_qty + quantity

        # 4. Проверка остатков (если у варианта ведётся учёт стока)
        stock = getattr(variant, 'stock', None)
        if stock is not None and new_qty > stock.quantity:
            raise ValidationError({
                'quantity': (
                    f'На складе доступно только {stock.quantity} шт., '
                    f'в корзине уже {current_qty}.'
                ),
            })

        # 5. Создание / обновление
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
        """
        # Выбираем с блокировкой и связанным стоком
        try:
            item = (
                CartItem.objects
                .select_for_update()
                .select_related('variant__stock')
                .get(pk=item_id, cart=cart)
            )
        except CartItem.DoesNotExist:
            raise NotFound('Позиция корзины не найдена.')

        stock = getattr(item.variant, 'stock', None)
        if stock is not None and quantity > stock.quantity:
            raise ValidationError({
                'quantity': f'На складе доступно только {stock.quantity} шт.',
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
        """Удаляет позицию из корзины."""
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
        """Полностью очищает корзину."""
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
        в корзину пользователя. Если у пользователя уже была
        активная корзина — количества суммируются.

        Возвращает корзину пользователя или None, если гостевой не было.

        Проверяет:
          - variant.is_active — пропускает деактивированные
          - сток — ограничивает quantity доступным остатком
          - лимит позиций — не превышает MAX_CART_ITEMS
        """
        session_hash = Cart.hash_session_key(session_key)
        guest_cart = (
            Cart.objects
            .select_for_update()
            .filter(session_key_hash=session_hash, is_active=True)
            .first()
        )
        if not guest_cart:
            logger.debug('cart_merge_skip: no guest cart')
            return None

        user_cart, _ = (
            Cart.objects
            .select_for_update()
            .get_or_create(user=user, is_active=True)
        )

        guest_items = (
            guest_cart.items
            .select_related('variant', 'variant__stock')
            .all()
        )

        merged_count = 0
        for guest_item in guest_items:
            # Пропускаем неактивные варианты
            if not guest_item.variant.is_active:
                logger.debug(
                    'cart_merge_skip_variant_inactive',
                    extra={'variant_id': guest_item.variant_id},
                )
                continue

            existing = (
                CartItem.objects
                .select_for_update()
                .filter(cart=user_cart, variant=guest_item.variant)
                .first()
            )
            target_qty = (
                (existing.quantity if existing else 0) + guest_item.quantity
            )

            # Ограничиваем стоком
            stock = getattr(guest_item.variant, 'stock', None)
            if stock is not None:
                target_qty = min(target_qty, stock.quantity)

            if target_qty <= 0:
                continue

            # Проверяем лимит позиций (только при создании новой)
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

        # Гостевую корзину деактивируем (не удаляем — аналитика)
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
