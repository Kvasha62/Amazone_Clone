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
# Без: TypeError при парсинге аннотаций типов на Python 3.9.
# 📖 https://peps.python.org/pep-0604/
from __future__ import annotations

# logging — структурированное логирование.
# 📖 https://docs.python.org/3/library/logging.html
import logging

# transaction.atomic — обёртка для SQL-транзакций.
# BEGIN; ... код ...; COMMIT; (или ROLLBACK при исключении).
# 📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
from django.db import transaction

# DRF-исключения — транслируются в HTTP-ответы:
#   NotFound → HTTP 404
#   ValidationError → HTTP 400
# View НЕ ловит эти исключения — DRF делает это автоматически.
# 📖 https://www.django-rest-framework.org/api-guide/exceptions/
from rest_framework.exceptions import NotFound, ValidationError

# MAX_CART_ITEMS — лимит позиций в корзине (100).
from apps.cart.constants import MAX_CART_ITEMS

# Cart, CartItem — модели корзины.
from apps.cart.models import Cart, CartItem

# ProductVariant — модель варианта товара (из catalog app).
from apps.catalog.models import ProductVariant

# Создаём логгер с именем модуля.
# В settings.py можно настроить уровень логирования:
#   'apps.cart.services': {'level': 'DEBUG'}
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

    📖 https://martinfowler.com/eaaCatalog/serviceLayer.html
    """

    # ----------------------------------------------------------
    # Получение / создание корзины
    # ----------------------------------------------------------

    @staticmethod
    # @transaction.atomic — оборачивает метод в SQL-транзакцию.
    # Зачем: get_or_create может создать корзину → если следующий код
    # упадёт → корзина откатится (ROLLBACK).
    # Без atomic: «пустая» корзина останется в БД → user потеряет
    # возможность создать новую (UniqueConstraint: одна активная корзина).
    # 📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
    @transaction.atomic
    def get_or_create_cart(request) -> Cart:
        """
        Возвращает активную корзину для текущего запроса.

        ДВА СЦЕНАРИЯ:
          1. Авторизованный: Cart.objects.get_or_create(user=request.user)
          2. Гость: Cart.objects.get_or_create(session_key_hash=hash)

        АРГУМЕНТ request — Django HttpRequest (или DRF Request).
          Содержит: request.user, request.session.

        get_or_create() — атомарная операция Django:
          try: get() → existing
          except DoesNotExist: create() → new
          Если два параллельных create() → IntegrityError → retry → get()
          📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#get-or-create

        NB: request.session.create() создаёт запись в django_session.
        При JWT-авторизации без session middleware это может не работать —
        используйте явный merge-эндпоинт (POST /cart/merge/).
        """
        if request.user.is_authenticated:
            # Авторизованный пользователь — ищем корзину по user.
            # get_or_create(user, is_active=True):
            #   если корзина есть → вернёт существующую (created=False)
            #   если нет → создаст новую (created=True)
            # UniqueConstraint гарантирует максимум одну активную корзину.
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                is_active=True,
            )
            return cart

        # ── Гость ──
        # Гарантируем наличие сессии.
        # request.session.session_key — текущий ключ сессии (может быть None).
        # request.session.create() — если ключа нет, создаёт запись
        # в django_session и назначает новый ключ.
        #
        # ПОБОЧНЫЙ ЭФФЕКТ: создаёт запись в django_session.
        # Для stateless API (pure REST без cookies) это избыточно.
        # Альтернатива: идентификатор корзины в заголовке X-Cart-Id
        # или в localStorage → без серверной сессии.
        # 📖 https://docs.djangoproject.com/en/stable/topics/http/sessions/
        if not request.session.session_key:
            request.session.create()

        # Хэшируем session_key → SHA-256.
        # Храним хэш, не raw-ключ → защита при утечке БД.
        session_hash = Cart.hash_session_key(request.session.session_key)

        # get_or_create по хэшу → одна активная корзина на гостя.
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

        ЗАЩИТА ОТ:
          • Неактивных / несуществующих вариантов (NotFound)
          • Неактивного товара (NotFound)
          • Превышения остатков (ValidationError)
          • Race conditions (select_for_update)
          • Превышения лимита позиций (ValidationError)
          • Отрицательного / нулевого quantity (ValidationError)

        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
        """

        # ── Шаг 0: Базовая валидация quantity ──
        # Проверяем ДО всех запросов к БД — быстро, бесплатно.
        # quantity < 1 → пользователь пытается добавить 0 или -5 товаров.
        if quantity < 1:
            raise ValidationError({
                'quantity': 'Количество должно быть не менее 1.',
            })

        # ── Шаг 1: Проверка лимита позиций ──
        # Считаем СУЩЕСТВУЮЩИЕ позиции до тяжёлых запросов.
        # MAX_CART_ITEMS = 100 — если уже 100 → нельзя добавить новую.
        # Если позиция уже есть (тот же variant) → count не изменится →
        # лимит не нарушится → проверяем ниже при создании.
        existing_count = cart.items.count()
        if existing_count >= MAX_CART_ITEMS:
            raise ValidationError({
                'detail': (
                    f'Максимум позиций в корзине — {MAX_CART_ITEMS}.'
                ),
            })

        # ── Шаг 2: Загрузка варианта с проверкой активности ──
        # select_related('product', 'stock') — JOIN в одном запросе:
        #   variant + product + stock = 1 SQL вместо 3.
        # get(pk=variant_id, is_active=True) — только активный вариант.
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related
        try:
            variant = (
                ProductVariant.objects
                .select_related('product', 'stock')
                .get(pk=variant_id, is_active=True)
            )
        except ProductVariant.DoesNotExist:
            # NotFound → HTTP 404. Вариант не найден или деактивирован.
            raise NotFound('Вариант товара не найден или неактивен.')

        # ── Шаг 3: Проверка что ТОВАР тоже активен ──
        # Вариант может быть is_active=True при DRAFT/ARCHIVED товаре.
        # variant.product загружен через select_related → нет доп. SQL.
        # 📖 ProductStatus: см. apps/catalog/constants.py
        from apps.catalog.constants import ProductStatus
        if variant.product.status != ProductStatus.ACTIVE:
            raise NotFound('Товар недоступен для заказа.')

        # ── Шаг 4: select_for_update — блокировка строки ──
        # ПЕССИМИСТИЧНАЯ БЛОКИРОВКА (pessimistic locking):
        #   SELECT ... FOR UPDATE WHERE cart=X AND variant=Y
        #   → PostgreSQL блокирует эту строку до COMMIT.
        #   → Другая транзакция с тем же cart+variant будет ЖДАТЬ.
        #
        # ЗАЧЕМ: два параллельных POST /cart/items/ с variant_id=5:
        #   Без FOR UPDATE:
        #     T1: SELECT → нет строки → quantity=0
        #     T2: SELECT → нет строки → quantity=0
        #     T1: INSERT quantity=3
        #     T2: INSERT quantity=2 → UniqueConstraint или дубликат!
        #   С FOR UPDATE:
        #     T1: SELECT FOR UPDATE → заблокировал
        #     T2: SELECT FOR UPDATE → ЖДЁТ
        #     T1: INSERT quantity=3 → COMMIT
        #     T2: SELECT FOR UPDATE → видит строку → UPDATE quantity=5
        #
        # .first() — вернёт None если строки нет (вместо DoesNotExist).
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
        # 📖 https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE
        item = (
            CartItem.objects
            .select_for_update()
            .select_related('variant', 'variant__stock')
            .filter(cart=cart, variant=variant)
            .first()
        )

        # Вычисляем новое количество:
        # Если позиции нет → current_qty = 0, new_qty = quantity
        # Если есть → current_qty = existing, new_qty = existing + quantity
        current_qty = item.quantity if item else 0
        new_qty = current_qty + quantity

        # ── Шаг 5: Проверка остатков на складе ──
        # getattr(variant, 'stock', None) — безопасный доступ к stock.
        # variant.stock загружен через select_related → без доп. SQL.
        # stock может быть None — у варианта нет складской записи
        # (inventory app ещё не создан / вариант не привязан к складу).
        stock = getattr(variant, 'stock', None)
        if stock is not None and new_qty > stock.quantity:
            raise ValidationError({
                'quantity': (
                    f'На складе доступно только {stock.quantity} шт., '
                    f'в корзине уже {current_qty}.'
                ),
            })

        # ── Шаг 6: Создание / обновление CartItem ──
        if item:
            # Позиция уже есть — ОБНОВЛЯЕМ количество.
            # update_fields=['quantity', 'updated_at'] — UPDATE только
            # этих полей, не всей строки. Быстрее и безопаснее.
            # updated_at — нужно обновить чтобы cleanup_expired_carts
            # правильно определял «старые» корзины.
            item.quantity = new_qty
            item.save(update_fields=['quantity', 'updated_at'])
        else:
            # Позиции нет — СОЗДАЁМ новую строку.
            item = CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=new_qty,
            )

        # Логируем операцию — для мониторинга и аналитики.
        # extra — структурированные данные для ELK / Datadog.
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

        ПОЧЕМУ РАЗНЫЕ ЗАПРОСЫ ДЛЯ variant и stock:
          variant — INNER JOIN (обязательный FK) → совместим с FOR UPDATE.
          stock — nullable (LEFT OUTER JOIN) → PostgreSQL ЗАПРЕЩАЕТ
          FOR UPDATE на nullable-стороне → ошибка:
            "FOR UPDATE cannot be applied to the nullable side of an outer join"
          Поэтому stock читаем ОТДЕЛЬНЫМ лёгким запросом.

        📖 https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE
        """
        # select_for_update() + select_related('variant')
        # INNER JOIN к variant (обязательный FK) → FOR UPDATE работает.
        # get(pk=item_id, cart=cart) — проверяем что item В ЭТОЙ корзине.
        # Если item чужой → DoesNotExist → NotFound → 404.
        try:
            item = (
                CartItem.objects
                .select_for_update()
                .select_related('variant')
                .get(pk=item_id, cart=cart)
            )
        except CartItem.DoesNotExist:
            raise NotFound('Позиция корзины не найдена.')

        # Сток читаем отдельным запросом (не в select_for_update).
        # Нам нужно только текущее значение stock.quantity.
        # Блокировка стока не нужна — мы только ЧИТАЕМ, не списываем.
        # Реальное списание произойдёт при оформлении заказа.
        variant = (
            ProductVariant.objects
            .select_related('stock')
            .filter(pk=item.variant_id)
            .first()
        )
        stock = getattr(variant, 'stock', None) if variant else None
        if stock is not None and quantity > stock.quantity:
            raise ValidationError({
                'quantity': f'На складе доступно только {stock.quantity} шт.',
            })

        # Обновляем количество.
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

        ВОЗВРАЩАЕТ None (не удалённый объект).
        Зачем: удаление — необратимая операция, нет смысла возвращать объект.

        .delete() — возвращает кортеж (count, {model: count}).
        count = 0 если ничего не удалено → NotFound.
        """
        # filter(pk=item_id, cart=cart) — проверяем что item В ЭТОЙ корзине.
        # Если передать item_id из чужой корзины → deleted=0 → NotFound.
        # Это защита от IDOR (Insecure Direct Object Reference):
        #   пользователь не может удалить чужую позицию.
        # 📖 https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
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

        cart.items.all().delete() — Django DELETE с CASCADE:
          DELETE FROM cart_cartitem WHERE cart_id = X
        Один SQL-запрос, независимо от количества позиций.
        """
        # items — related_name на CartItem.cart.
        # .all().delete() — DELETE WHERE cart_id = X
        # 📖 https://docs.djangoproject.com/en/stable/topics/db/queries/#deleting-objects
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

        ВОЗВРАЩАЕТ:
          Cart — корзину пользователя (с добавленными позициями)
          None — если гостевой корзины не было

        Идемпотентность:
          Повторный вызов с тем же session_key → None (гостевая уже деактивирована).

        📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
        """
        # Хэшируем session_key для поиска.
        session_hash = Cart.hash_session_key(session_key)

        # select_for_update() — блокируем гостевую корзину.
        # Зачем: если два запроса одновременно логинят одного user
        # с одним session_key → оба найдут одну корзину →
        # могут слить дважды. FOR UPDATE → второй ждёт.
        guest_cart = (
            Cart.objects
            .select_for_update()
            .filter(session_key_hash=session_hash, is_active=True)
            .first()
        )
        if not guest_cart:
            # Нет гостевой корзины → нечего сливать.
            logger.debug('cart_merge_skip: no guest cart')
            return None

        # select_for_update() — блокируем юзерскую корзину.
        # get_or_create → если нет корзины → создаст.
        user_cart, _ = (
            Cart.objects
            .select_for_update()
            .get_or_create(user=user, is_active=True)
        )

        # Загружаем все позиции гостевой корзины с variant.
        # select_related — JOIN в одном запросе для оптимизации.
        guest_items = (
            guest_cart.items
            .select_related('variant', 'variant__stock')
            .all()
        )

        from apps.catalog.constants import ProductStatus

        merged_count = 0
        for guest_item in guest_items:
            # ── Проверка: вариант активен? ──
            # Неактивный вариант → пропускаем (не добавляем в юзерскую).
            if not guest_item.variant.is_active:
                logger.debug(
                    'cart_merge_skip_variant_inactive',
                    extra={'variant_id': guest_item.variant_id},
                )
                continue

            # ── Проверка: товар доступен? ──
            # variant__product загружен через select_related (variant → product).
            # Нужен INNER JOIN к product — stock тоже нужен ниже.
            if guest_item.variant.product.status != ProductStatus.ACTIVE:
                logger.debug(
                    'cart_merge_skip_product_unavailable',
                    extra={'product_id': guest_item.variant.product_id},
                )
                continue

            # ── Ищем такую же позицию в юзерской корзине ──
            # select_for_update — блокируем строку до конца транзакции.
            existing = (
                CartItem.objects
                .select_for_update()
                .filter(cart=user_cart, variant=guest_item.variant)
                .first()
            )

            # Вычисляем целевое количество:
            # если позиция есть → сложить, если нет → quantity гостевой
            target_qty = (
                (existing.quantity if existing else 0) + guest_item.quantity
            )

            # ── Ограничиваем стоком ──
            # variant.stock загружен через select_related → без доп. SQL.
            stock = getattr(guest_item.variant, 'stock', None)
            if stock is not None:
                # min(target_qty, stock.quantity) — не превышаем остаток.
                target_qty = min(target_qty, stock.quantity)

            # Если после ограничения стоком quantity ≤ 0 → пропускаем.
            if target_qty <= 0:
                continue

            # ── Проверяем лимит позиций (только при создании новой) ──
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
                    # Пропускаем эту позицию, но продолжаем с остальными.
                    continue

            # ── Создание / обновление позиции в юзерской корзине ──
            if existing:
                # Обновляем количество существующей позиции.
                existing.quantity = target_qty
                existing.save(update_fields=['quantity', 'updated_at'])
            else:
                # Создаём новую позицию.
                CartItem.objects.create(
                    cart=user_cart,
                    variant=guest_item.variant,
                    quantity=target_qty,
                )

            merged_count += 1

        # Гостевую корзину ДЕАКТИВИРУЕМ (не удаляем!).
        # Почему: аналитика «сколько корзин слилось» + возможность восстановления.
        # Удалится позже через cleanup_expired_carts (через 30 дней).
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
