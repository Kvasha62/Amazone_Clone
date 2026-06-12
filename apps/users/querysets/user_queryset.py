# ────────────────────────────────────────────────────────────────────────
# apps/users/querysets/user_queryset.py — QuerySet пользователя.
#
# Оптимизированные выборки для API:
#   with_profile    — select_related OneToOne (1 запрос вместо 2)
#   active          — filter(is_active=True)
#   by_email        — case-insensitive поиск по email
#   with_addresses  — prefetch_related M2M-like (FK, один-ко-многим)
#   full            — with_profile + with_addresses
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related
# ────────────────────────────────────────────────────────────────────────

# models.QuerySet — базовый класс для цепочечных запросов.
from django.db import models


class UserQuerySet(models.QuerySet):
    """
    QuerySet-методы для модели User.
    Доступны через User.objects.* благодаря from_queryset().
    """

    def with_profile(self):
        """
        Подтягивает OneToOne профиль (1 запрос).

        select_related для OneToOne = INNER JOIN в том же SELECT:
          SELECT user.*, profile.* FROM users_user
          LEFT JOIN users_profile ON ... WHERE ...

        Без: user.profile → отдельный SQL (N+1 при списке пользователей).
        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related
        """
        return self.select_related('profile')

    def active(self):
        """
        Только активные (не заблокированные) пользователи.

        is_active=True — пользователь может логиниться.
        is_active=False — заблокирован / деактивировал аккаунт.
        """
        return self.filter(is_active=True)

    def by_email(self, email: str):
        """
        Поиск по email (case-insensitive).

        __iexact — SQL: WHERE email ILIKE 'test@example.com'
        ('T' совпадает с 't', 'E' с 'e' и т.д.)

        ПОЧЕМУ НЕ __exact:
          Пользователь регистрируется как «Test@Example.com»,
          логинится как «test@example.com» → без iexact — не найдёт!

        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#iexact
        """
        return self.filter(email__iexact=email)

    def with_addresses(self):
        """
        Prefetch адресов доставки.

        prefetch_related для FK (один-ко-многим):
          SELECT * FROM users_address WHERE user_id IN (...)

        Без: user.addresses.all() → N запросов на N пользователей.
        📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related
        """
        return self.prefetch_related('addresses')

    def full(self):
        """
        Полная загрузка: профиль + адреса.

        Композитный метод: with_profile() + with_addresses()
        = SELECT user.*, profile.* + prefetch addresses
        = 2 SQL-запроса вместо 1 + N + M.
        """
        return self.with_profile().with_addresses()
