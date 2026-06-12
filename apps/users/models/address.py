# ────────────────────────────────────────────────────────────────────────
# apps/users/models/address.py — адрес доставки.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Пользователь может иметь несколько адресов (FK, не OneToOne)
#   • Один адрес — «по умолчанию» (is_default=True)
#   • При is_default=True → автоматически снимается с других адресов
#   • При создании заказа адрес КОПИРУЕТСЯ (не ссылка!) — если пользователь
#     изменит адрес, заказ сохранит старые данные.
#
# АВТОМАТИЧЕСКОЕ УПРАВЛЕНИЕ is_default:
#   Переопределённый save() снимает is_default с других адресов
#   при установке текущего как default. Это гарантирует инвариант:
#   «максимум один is_default=True на пользователя».
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/instances/#overriding-model-methods
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#foreignkey
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Таблица users_address не создастся
#   • AddressService → ImportError
#   • GET /users/addresses/ → 500
# ────────────────────────────────────────────────────────────────────────

# settings — для AUTH_USER_MODEL (best practice: не импортируем User напрямую).
from django.conf import settings

# models — ORM Django.
from django.db import models

# BaseModel — created_at + updated_at.
from apps.core.models.base_model import BaseModel

# MAX_ADDRESSES_PER_USER — лимит (10). Используется в AddressService.
from apps.users.constants import MAX_ADDRESSES_PER_USER


class Address(BaseModel):
    """
    Адрес доставки пользователя.

    Один из адресов может быть is_default=True.
    При создании заказа копируется — адрес в заказе не ссылается на эту модель.

    ПОЧЕМУ КОПИРОВАНИЕ, А НЕ FK:
      Пользователь может изменить адрес (улицу, город) после заказа.
      Если заказ ссылается на Address по FK → данные заказа изменятся!
      Копирование при оформлении → заказ сохраняет snapshot адреса.
    """

    # user — FK к модели пользователя.
    # on_delete=CASCADE — при удалении пользователя удаляем все его адреса.
    # related_name='addresses' → user.addresses.all()
    # settings.AUTH_USER_MODEL — 'users.User' (lazy reference).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Пользователь',
    )

    # recipient_name — ФИО получателя. Может отличаться от имени пользователя!
    # Например: пользователь «Иван Иванов» отправляет подарок «Марии Петровой».
    # CheckConstraint гарантирует что поле не пустое.
    recipient_name = models.CharField(
        verbose_name='ФИО получателя',
        max_length=200,
    )

    # Компоненты адреса разбиты на отдельные поля для:
    #   • Валидации (город обязателен, регион — нет)
    #   • Форматирования (разный порядок для разных стран)
    #   • Поиска (фильтр по городу без парсинга строки)
    # 📖 https://en.wikipedia.org/wiki/Address_(geography)#Address_format

    country = models.CharField(
        verbose_name='Страна',
        max_length=100,
        default='Россия',  # Целевая аудитория проекта — РФ
    )
    region = models.CharField(
        verbose_name='Регион / область',
        max_length=100,
        blank=True,
        default='',  # Москва — не регион (ФИАС)
    )
    city = models.CharField(
        verbose_name='Город',
        max_length=100,
    )
    street = models.CharField(
        verbose_name='Улица, дом, квартира',
        max_length=300,  # Длинное поле: «пр-т Мира, д. 123, стр. 4, кв. 567»
    )
    postal_code = models.CharField(
        verbose_name='Почтовый индекс',
        max_length=20,  # Разные страны — разная длина: РФ=6, US=5(+4)
        blank=True,
        default='',
    )

    # notes — дополнительная информация для курьера.
    # Пример: «Код домофона 123К, 3-й подъезд, 5-й этаж»
    notes = models.TextField(
        verbose_name='Примечания',
        blank=True,
        default='',
        help_text='Код домофона, ориентиры и т.д.',
    )

    # is_default — флаг адреса по умолчанию.
    # Инвариант: максимум ОДИН is_default=True на пользователя.
    # Поддерживается через save() — снимается с других при установке.
    # db_index=True — ускоряет: Address.objects.filter(user=X, is_default=True)
    is_default = models.BooleanField(
        verbose_name='По умолчанию',
        default=False,
        db_index=True,
    )

    class Meta:
        db_table = 'users_address'
        verbose_name = 'Адрес доставки'
        verbose_name_plural = 'Адреса доставки'
        # Сортировка: сначала default, потом по дате создания.
        # '-is_default' = True (1) идёт первым, False (0) — после.
        ordering = ('-is_default', '-created_at',)
        indexes = [
            # Составной индекс (user, is_default) — для запроса:
            #   Address.objects.filter(user=X, is_default=True)
            models.Index(
                fields=['user', 'is_default'],
                name='users_address_user_default_idx',
            ),
        ]
        constraints = [
            # CheckConstraint: recipient_name не пустой.
            # Q(recipient_name__gt='') — строка длиннее пустой.
            # Без: можно создать адрес с recipient_name='' → бесполезная запись.
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
            models.CheckConstraint(
                condition=models.Q(recipient_name__gt=''),
                name='address_recipient_name_required',
            ),
        ]

    def __str__(self):
        """«Москва, ул. Тестовая, д. 1 (123456)»."""
        parts = [self.city, self.street]
        if self.postal_code:
            parts.append(f'({self.postal_code})')
        return ', '.join(parts)

    def clean(self):
        """
        Python-валидация (для Admin / форм).
        Дублирует CheckConstraint на уровне Python → дружелюбное сообщение.
        """
        super().clean()
        from django.core.exceptions import ValidationError
        if not self.recipient_name or not self.recipient_name.strip():
            raise ValidationError({'recipient_name': 'Укажите ФИО получателя.'})

    def save(self, **kwargs):
        """
        Переопределённый save() — управляет инвариантом is_default.

        АЛГОРИТМ:
          Если this.is_default == True:
            1. Снять is_default со ВСЕХ других адресов этого пользователя
            2. Сохранить текущий адрес

        ПОЧЕМУ В save(), А НЕ В СЕРВИСЕ:
          Гарантирует инвариант на уровне модели — даже при прямом ORM-вызове:
            Address(is_default=True, ...).save()
          Без: можно установить is_default=True двум адресам через admin/shell.

        .exclude(pk=self.pk) — не снимать default с САМОГО себя при обновлении.
        Без exclude: UPDATE ... WHERE id = self.pk → снимет с себя же!

        .update(is_default=False) — прямой SQL, без вызова save() других адресов.
        📖 https://docs.djangoproject.com/en/stable/ref/models/instances/#overriding-model-methods
        """
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(**kwargs)
