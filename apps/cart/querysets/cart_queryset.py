# ────────────────────────────────────────────────────────────────────────
# apps/cart/querysets/cart_queryset.py — QuerySet корзины.
#
# Методы строят оптимальные SQL-запросы к таблице cart_cart.
# Каждый метод возвращает НОВЫЙ QuerySet (composability):
#   Cart.objects.active().with_items()
#   Cart.objects.for_user(user).full()
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#from-queryset
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/
# 📖 select_related vs prefetch_related:
#   https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related
#   https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • CartManager не сможет from_queryset(CartQuerySet) → ImportError
#   • Все методы Cart.objects.active(), .full(), .with_items() → N/A
# ────────────────────────────────────────────────────────────────────────

# models.QuerySet — базовый класс Django для построения SQL-запросов.
from django.db import models

# Prefetch — кастомный prefetch_related с собственным QuerySet.
# Позволяет задать фильтры/порядок для prefetch-набора.
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-objects
from django.db.models import Prefetch


class CartQuerySet(models.QuerySet):
    """
    QuerySet корзины. Оптимизирует выборку для API.

    Используется через CartManager (from_queryset).

    Методы:
        active()         — только активные корзины
        for_user()       — активная корзина пользователя
        for_session()    — активная корзина гостя
        with_items()     — prefetch всех связей (без фильтра is_active)
        full()           — active() + with_items() — для listing / поиска

    📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/
    """

    def active(self):
        """
        Только активные корзины (is_active=True).

        ПОЧЕМУ ЭТОТ ФИЛЬТР ПЕРВИЧНЫЙ:
          99% запросов к корзине = «дай мне активную корзину».
          Неактивные корзины = мусор/архив — нужны только в admin/analytics.

        БЕЗ ЭТОГО МЕТОДА:
          Cart.objects.filter(is_active=True) в каждом месте → дублирование.
        """
        # filter() возвращает новый QuerySet (SQL НЕ выполняется!).
        return self.filter(is_active=True)

    def for_user(self, user):
        """
        Активная корзина авторизованного пользователя.

        АРГУМЕНТ user — объект User (не id).
          Django автоматически извлечёт user.pk → WHERE user_id = X.

        БЕЗ: Cart.objects.filter(user=user, is_active=True) повсюду.
        """
        # .active() — вызываем наш метод (composability!)
        # .filter(user=user) — WHERE user_id = X
        return self.active().filter(user=user)

    def for_session(self, session_key_hash: str):
        """
        Активная корзина гостя по хэшу session_key.

        АРГУМЕНТ session_key_hash — УЖЕ хэшированная строка (64 символа).
          НЕ raw session_key! Хэширование делается в CartService.

        📖 про session_key_hash: см. apps/cart/models/cart.py
        """
        return self.active().filter(session_key_hash=session_key_hash)

    def with_items(self):
        """
        Подгружает элементы корзины со ВСЕМИ связями за минимум запросов.

        СТРУКТУРА СВЯЗЕЙ:
            Cart
            └── CartItem                     (prefetch_related)
                    └── ProductVariant       (select_related)
                            ├── Product      (select_related)
                            │    └── Brand   (select_related)
                            ├── Price        (select_related, nullable)
                            └── Stock        (select_related, nullable)

        ПОЧЕМУ НЕ ФИЛЬТРУЕТ по is_active:
          Этот метод используется для сериализации КОНКРЕТНОЙ корзины
          по PK (активность уже проверена выше по цепочке).
          Если добавить .filter(items__variant__is_active=True) →
          INNER JOIN → позиции с неактивными вариантами ИСЧЕЗНУТ
          из корзины — пользователь увидит «пустую» корзину,
          хотя позиции есть (просто вариант деактивирован).

        ПОЧЕМУ LAZY-ИМПОРТ CartItem:
          CartItem → ссылается на Cart (FK).
          Cart → импортирует CartManager → CartManager.from_queryset(CartQuerySet).
          Если импортировать CartItem наверху → цикл:
            cart.models → cart.querysets → cart.models → ♻️
          Lazy-импорт разрывает цикл: импорт при ВЫЗОВЕ, не при загрузке.
          📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package

        КОЛИЧЕСТВО SQL-ЗАПРОСОВ:
          Без оптимизации:
            1 (Cart) + N (CartItem) + N (Variant) + N (Product) + N (Brand)
            = 1 + 4N запросов. При 50 позициях = 201 запрос!
          С оптимизацией:
            1 (Cart + CartItem + Variant + Product + Brand — все через JOIN)
            + 1 (Price, если select_related)
            = 1-2 запроса. При 50 позициях = 2 запроса!
          📖 https://docs.djangoproject.com/en/stable/topics/db/queries/#querysets-are-lazy
        """
        # Lazy-импорт — разрываем циклическую зависимость.
        from apps.cart.models import CartItem

        # Строим QuerySet для CartItem с глубокой оптимизацией.
        items_qs = (
            CartItem.objects
            # select_related — JOIN в ОДНОМ запросе для FK/OneToOne:
            #   variant         → catalog_productvariant (FK)
            #   variant__product → catalog_product (FK через variant)
            #   variant__product__brand → catalog_brand (FK через product→variant)
            #   variant__price  → pricing-модель (FK, может быть NULL)
            #   variant__stock  → inventory-модель (FK, может быть NULL)
            # Без select_related: каждый item.variant → 1 SQL = N запросов.
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related
            .select_related(
                'variant',                    # JOIN catalog_productvariant
                'variant__product',           # → JOIN catalog_product
                'variant__product__brand',    # → → JOIN catalog_brand
                'variant__price',             # → JOIN pricing-модель
                'variant__stock',             # → JOIN inventory-модель
            )
            # Сортировка: новые позиции первыми.
            .order_by('-created_at')
        )

        # Prefetch('items', queryset=items_qs) — кастомный prefetch.
        # Вместо стандартного items_qs Django использует наш items_qs.
        # Это позволяет:
        #   1) Фильтровать prefetch (только определённые items)
        #   2) Оптимизировать prefetch (select_related внутри)
        #   3) Сортировать prefetch (order_by)
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related
        return self.prefetch_related(
            Prefetch('items', queryset=items_qs)
        )

    def full(self):
        """
        Полная версия корзины — для отдачи в API / listing.
        Гарантирует отсутствие N+1.

        КОМПОЗИТНЫЙ МЕТОД:
          active() — фильтр по is_active
          with_items() — prefetch всех связей
          Вместе = оптимальный запрос для API-ответа.

        БЕЗ ЭТОГО МЕТОДА:
          В каждой view: Cart.objects.active().with_items() — дублирование.
        """
        return self.active().with_items()
