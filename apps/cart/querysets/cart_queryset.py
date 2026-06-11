from django.db import models
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
    """

    def active(self):
        """Только активные корзины."""
        return self.filter(is_active=True)

    def for_user(self, user):
        """Активная корзина авторизованного пользователя."""
        return self.active().filter(user=user)

    def for_session(self, session_key_hash: str):
        """Активная корзина гостя по хэшу session_key."""
        return self.active().filter(session_key_hash=session_key_hash)

    def with_items(self):
        """
        Подгружает элементы корзины со всеми связями за минимум запросов:

            Cart
            └── CartItem
                    └── ProductVariant
                            ├── Product (+ Brand)
                            ├── Price
                            └── Stock

        НЕ фильтрует по is_active — используется для сериализации
        конкретной корзины по PK (активность уже проверена выше).

        Импорт CartItem делается локально, чтобы избежать
        циклических импортов на старте Django.
        """
        from apps.cart.models import CartItem

        items_qs = (
            CartItem.objects
            .select_related(
                'variant',
                'variant__product',
                'variant__product__brand',
                'variant__price',
                'variant__stock',
            )
            .order_by('-created_at')
        )

        return self.prefetch_related(
            Prefetch('items', queryset=items_qs)
        )

    def full(self):
        """
        Полная версия корзины — для отдачи в API / listing.
        Гарантирует отсутствие N+1.
        """
        return self.active().with_items()
