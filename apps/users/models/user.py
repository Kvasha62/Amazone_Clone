# ────────────────────────────────────────────────────────────────────────
# apps/users/models/user.py — кастомная модель пользователя.
#
# КЛЮЧЕВОЕ АРХИТЕКТУРНОЕ РЕШЕНИЕ:
#   Проект использует AUTH_USER_MODEL = 'users.User' в settings.py.
#   Это позволяет заменить стандартную django.contrib.auth.models.User
#   на нашу кастомную модель с дополнительными полями (phone, email).
#
#   ВАЖНО: User наследует AbstractUser (НЕ BaseModel!).
#   AbstractUser уже имеет: username, email, first_name, last_name,
#   is_active, is_staff, is_superuser, date_joined, last_login.
#   У AbstractUser НЕТ updated_at — поэтому мы НЕ можем использовать
#   update_fields=['updated_at'] при сохранении User.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#substituting-a-custom-user-model
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/auth/#django.contrib.auth.models.AbstractUser
# 📖 https://docs.djangoproject.com/en/stable/ref/settings/#auth-user-model
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Django не сможет загрузить пользователя → ImportError
#   • AUTH_USER_MODEL = 'users.User' → LookupError
#   • Все модели с FK к User → crash
# ────────────────────────────────────────────────────────────────────────

# AbstractUser — базовый класс Django с полным набором полей пользователя:
# username, email (не required!), first_name, last_name, is_active,
# is_staff, is_superuser, date_joined, last_login, groups, user_permissions.
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/auth/#django.contrib.auth.models.AbstractUser
from django.contrib.auth.models import AbstractUser

# models — ORM Django.
from django.db import models

# UserManager — кастомный менеджер с QuerySet-методами (with_profile, active, ...).
from apps.users.managers.user_manager import UserManager


class User(AbstractUser):
    """
    Кастомная модель пользователя.

    Заменяет стандартную django.contrib.auth.models.User через
    AUTH_USER_MODEL = 'users.User' в settings.py.

    ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ (по сравнению со стандартным AbstractUser):
      • phone — номер телефона (опционально)
      • email — ПЕРЕОПРЕДЕЛЁН: обязателен, уникален (в стандартном — blank=True)

    ВАЖНО: AbstractUser НЕ наследует BaseModel → у User НЕТ полей
    created_at / updated_at. Есть только date_joined (от AbstractUser).

    📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#substituting-a-custom-user-model
    """

    # objects = UserManager() — подменяет стандартный Manager.
    # UserManager наследует BaseUserManager (с create_user / create_superuser)
    # и добавляет методы из UserQuerySet (with_profile, active, by_email, ...).
    # 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
    objects = UserManager()

    # phone — номер телефона. Опциональное поле (blank=True, default='').
    # max_length=20 — достаточно для международных номеров: +7 (999) 123-45-67
    # или +1-202-555-0109. E.164 формат — до 15 цифр + символы.
    # 📖 https://en.wikipedia.org/wiki/E.164
    phone = models.CharField(
        verbose_name='Телефон',
        max_length=20,
        blank=True,
        default='',
    )

    # Переопределяем email из AbstractUser.
    # В стандартном AbstractUser: email = models.EmailField(blank=True)
    # → email НЕ обязательный, НЕ уникальный.
    # Мы делаем: unique=True (нет blank=True) → обязателен, уникален.
    #
    # ПОЧЕМУ EMAIL ОБЯЗАТЕЛЕН:
    #   • Восстановление пароля — нужен email
    #   • Email-рассылка — нужен email
    #   • Идентификация — email уникален, в отличие от username
    #
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#emailfield
    email = models.EmailField(
        verbose_name='Email',
        unique=True,
    )

    class Meta:
        # db_table — явно задаём имя таблицы (без этого Django создал бы
        # auth_user, что конфликтует со стандартной моделью при миграциях).
        db_table = 'users_user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        # ordering — новые пользователи первыми.
        ordering = ('-date_joined',)
        indexes = [
            # Индекс по email — ускоряет login, поиск, фильтрацию.
            # unique=True на EmailField уже создаёт unique index,
            # но отдельный Index может быть полезен для composite queries.
            models.Index(
                fields=['email'],
                # Имя ≤ 30 символов: users_user_email_idx = 20 ✅
                name='users_user_email_idx',
            ),
        ]

    def __str__(self):
        """
        Строковое представление — email (основной идентификатор).

        Если email пуст (маловероятно, т.к. required) → fallback на username.
        """
        return self.email or self.username

    @property
    def full_name(self) -> str:
        """
        Полное имя: «Иван Иванов».
        Если оба имени пустые → fallback на email.

        @property — доступ как к атрибуту: user.full_name
        📖 https://docs.python.org/3/library/functions.html#property
        """
        parts = [self.first_name, self.last_name]
        # filter(None, parts) — убирает пустые строки.
        # ' '.join(...) — склеивает через пробел.
        return ' '.join(filter(None, parts)) or self.email
