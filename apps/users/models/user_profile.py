# ────────────────────────────────────────────────────────────────────────
# apps/users/models/user_profile.py — расширенный профиль пользователя.
#
# АРХИТЕКТУРНЫЙ ПРИНЦИП «Profile Model»:
#   User (AbstractUser) — ядро: авторизация, email, пароль.
#   UserProfile (BaseModel) — расширение: аватар, день рождения, preferences.
#
#   ПОЧЕМУ НЕ ВСЕ ПОЛЯ В User:
#     • User используется при КАЖДОМ запросе (auth middleware).
#     • Загрузка 20+ полей ради проверки is_authenticated — расточительно.
#     • OneToOne позволяет загружать профиль ТОЛЬКО когда нужен:
#       User.objects.with_profile() — JOIN; без with_profile — без JOIN.
#
# СОЗДАНИЕ ПРОФИЛЯ:
#   Сигнал post_save на User → UserProfile.objects.get_or_create(user=instance).
#   📖 apps/users/signals.py
#
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#extending-the-existing-user-model
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#imagefield
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • UserProfile.DoesNotExist в сериализаторах
#   • user.profile → RelatedObjectDoesNotExist
#   • GET /users/me/ → 500
# ────────────────────────────────────────────────────────────────────────

# settings — для AUTH_USER_MODEL (Django best practice).
from django.conf import settings

# models — ORM Django.
from django.db import models

# BaseModel — абстрактная модель с created_at + updated_at.
# ВНИМАНИЕ: UserProfile наследует BaseModel (а User — AbstractUser).
# Поэтому у UserProfile ЕСТЬ updated_at, а у User — НЕТ.
from apps.core.models.base_model import BaseModel


class UserProfile(BaseModel):
    """
    Расширенный профиль пользователя.

    Создаётся автоматически через сигнал post_save при создании User.
    OneToOne → у каждого User ровно один UserProfile.

    📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#extending-the-existing-user-model
    """

    # TextChoices — Enum для пола. Используется в choices= и в сериализаторах.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#enumeration-types
    class GenderChoices(models.TextChoices):
        MALE = 'M', 'Мужской'       # 'M' → значение в БД, 'Мужской' → отображение
        FEMALE = 'F', 'Женский'
        OTHER = 'O', 'Другой'

    # user — OneToOne к модели пользователя.
    # on_delete=CASCADE — при удалении пользователя удаляем профиль.
    # related_name='profile' → user.profile → доступ к профилю.
    # settings.AUTH_USER_MODEL — строка 'users.User' (lazy, без прямого импорта).
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#onetoonefield
    # 📖 https://docs.djangoproject.com/en/stable/ref/settings/#auth-user-model
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )

    # avatar — изображение профиля.
    # ImageField — использует Pillow для валидации (только изображения).
    # upload_to='avatars/%Y/%m/' — путь: MEDIA_ROOT/avatars/2026/06/filename.jpg
    # %Y/%m — год/месяц для автоматической организации файлов.
    # blank=True, null=True — аватар необязателен.
    #
    # ВНИМАНИЕ: нужен Pillow (pip install Pillow). Без: ImportError.
    # В проде: рекомендуется S3 (django-storages) вместо локального хранилища.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#imagefield
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
    )

    # date_of_birth — дата рождения (для персонализации, скидок).
    # null=True, blank=True — необязательное поле.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#datefield
    date_of_birth = models.DateField(
        verbose_name='Дата рождения',
        null=True,
        blank=True,
    )

    # gender — пол (выбор из GenderChoices).
    # max_length=1 — 'M', 'F', 'O' (один символ).
    # blank=True, default='' — поле необязательное.
    gender = models.CharField(
        verbose_name='Пол',
        max_length=1,
        choices=GenderChoices.choices,
        blank=True,
        default='',
    )

    # timezone — часовой пояс пользователя.
    # Используется для отображения времени в заказах, уведомлениях.
    # default='UTC' — безопасное значение по умолчанию.
    # 📖 https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    timezone = models.CharField(
        verbose_name='Часовой пояс',
        max_length=50,
        blank=True,
        default='UTC',
    )

    # language — предпочитаемый язык интерфейса.
    # default='ru' — русский по умолчанию (целевая аудитория проекта).
    language = models.CharField(
        verbose_name='Язык',
        max_length=10,
        blank=True,
        default='ru',
    )

    # email_subscribed — подписка на email-рассылку.
    # default=False — по умолчанию НЕ подписан (GDPR / закон о рекламе).
    # 📖 https://gdpr-info.eu/
    email_subscribed = models.BooleanField(
        verbose_name='Email-рассылка',
        default=False,
    )

    class Meta:
        db_table = 'users_profile'
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ('-created_at',)

    def __str__(self):
        """«Профиль test@example.com»."""
        return f'Профиль {self.user}'
