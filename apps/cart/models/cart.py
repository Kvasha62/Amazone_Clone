# ────────────────────────────────────────────────────────────────────────
# apps/cart/models/cart.py — модель корзины покупателя.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • У каждого пользователя/гостя — ОДНА активная корзина (UniqueConstraint)
#   • Гостевые корзины идентифицируются по session_key (хэш SHA-256)
#   • Владелец обязателен: либо user, либо session_key_hash (CheckConstraint)
#   • Корзина «мягко» деактивируется при merge (не удаляется — аналитика)
#
# БЕЗОПАСНОСТЬ:
#   session_key_hash — SHA-256 хэш ключа сессии.
#   Храним хэш, а не raw-ключ: если БД скомпрометирована →
#   злоумышленник получит хэши, но не сможет подменить сессию.
#   📖 https://docs.djangoproject.com/en/stable/topics/http/sessions/
#   📖 https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
#
# БАЗОВАЯ МОДЕЛЬ:
#   Cart наследует BaseModel → получает created_at + updated_at автоматически.
#   📖 про BaseModel — см. apps/core/models/base_model.py
#
# 📖 Про UniqueConstraint: https://docs.djangoproject.com/en/stable/ref/models/constraints/#uniqueconstraint
# 📖 Про CheckConstraint:  https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
# 📖 Про partial indexes:   https://www.postgresql.org/docs/current/indexes-partial.html
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Таблица cart_cart не создастся → CartItem не сможет ссылаться на Cart
#   • Все сервисы, views, сериализаторы корзины → ImportError
# ────────────────────────────────────────────────────────────────────────

# hashlib — стандартная библиотека Python для криптографических хэшей.
# Используем SHA-256 для хэширования session_key.
# 📖 https://docs.python.org/3/library/hashlib.html
import hashlib

# get_user_model() — функция Django для получения активной модели User.
# НЕ используем from django.contrib.auth.models import User —
# потому что проект может использовать кастомную модель пользователя
# (AUTH_USER_MODEL = 'users.User' в settings.py).
# get_user_model() возвращает РЕАЛЬНУЮ модель, а не обязательно auth.User.
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#django.contrib.auth.get_user_model
from django.contrib.auth import get_user_model

# ValidationError — Django-исключение для ошибок валидации на уровне модели.
# Отличается от rest_framework.exceptions.ValidationError!
# Django ValidationError → используется в Model.clean(), формах, админке.
# DRF ValidationError → используется в сериализаторах и API.
# 📖 https://docs.djangoproject.com/en/stable/ref/validators/#django.core.exceptions.ValidationError
from django.core.exceptions import ValidationError

# models — ORM Django: поля, связи, индексы, constraints.
from django.db import models

# Q — объект для построения сложных условий (AND/OR/NOT).
# Используем в UniqueConstraint condition=Q(...) и CheckConstraint.
# 📖 https://docs.djangoproject.com/en/stable/topics/db/queries/#complex-lookups-with-q-objects
from django.db.models import Q

# BaseModel — абстрактная модель с created_at + updated_at.
# 📖 см. apps/core/models/base_model.py
from apps.core.models import BaseModel

# CartManager — кастомный менеджер с QuerySet-методами (active, full, with_items).
# Подключается к Cart через objects = CartManager().
from apps.cart.managers.cart_manager import CartManager

# Получаем класс модели пользователя (не экземпляр!).
# User = get_user_model() сработает только если модели уже загружены.
# На верхнем уровне модуля это безопасно — Django загружает модели до ready().
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#referencing-the-user-model
User = get_user_model()


# ==========================================================
# КОРЗИНА
# ==========================================================

class Cart(BaseModel):
    """
    Корзина пользователя (shopping cart).

    ДВА ТИПА ВЛАДЕЛЬЦА:
      1. Авторизованный пользователь (user != None, session_key_hash = None)
      2. Гость (user = None, session_key_hash != None)

    ИНВАРИАНТЫ (гарантируются БД через constraints):
      • У одного юзера — максимум ОДНА активная корзина
      • У одной сессии — максимум ОДНА активная корзина
      • Должен быть указан хотя бы один владелец (user ИЛИ session_key_hash)

    ЖИЗНЕННЫЙ ЦИКЛ:
      1. Гость добавляет товар → создаётся гостевая корзина
      2. Гость логинится → CartService.merge_guest_into_user_cart()
         → гостевая деактивируется, позиции переносятся в юзерскую
      3. Юзер оформляет заказ → корзина деактивируется (не удаляется)
      4. cleanup_expired_carts → неактивные корзины удаляются через 30 дней

    📖 https://docs.djangoproject.com/en/stable/topics/db/models/
    """

    # objects = CartManager() — подменяет стандартный менеджер Django.
    # Без: Cart.objects.active() → AttributeError (у Manager нет метода active).
    # CartManager создан через from_queryset(CartQuerySet) →
    # все методы CartQuerySet доступны через Cart.objects.
    # 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
    objects = CartManager()

    # user — FK к модели пользователя.
    # null=True, blank=True — разрешаем NULL (гостевая корзина без юзера).
    # on_delete=CASCADE — при удалении юзера удаляем все его корзины.
    #   (Альтернатива: SET_NULL — корзка остаётся «сиротой».
    #    Но сироты засоряют БД → CASCADE чище.)
    # related_name='carts' → user.carts.all() — все корзины пользователя.
    # verbose_name — для Admin UI и форм.
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#foreignkey
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name='Пользователь',
    )

    # session_key_hash — SHA-256 хэш ключа сессии Django.
    #
    # ПОЧЕМУ ХЭШ, А НЕ РОДНОЙ session_key:
    #   Django session_key = 40-символьная строка (по умолчанию).
    #   Если хранить raw-ключ в БД и БД утечёт →
    #   злоумышленник подставит sessionid=... в cookie →
    #   получит доступ к корзине (а может и к аккаунту).
    #   SHA-256 необратим → по хэшу нельзя восстановить ключ.
    #
    # max_length=64 — SHA-256 hex = ровно 64 символа.
    #   SHA-256 = 256 бит = 32 байта = 64 hex-символа.
    #   📖 https://en.wikipedia.org/wiki/SHA-2
    #
    # db_index=True — создаёт B-tree индекс для быстрого поиска:
    #   Cart.objects.filter(session_key_hash='abc123...')
    #   Без индекса → полное сканирование таблицы (Seq Scan).
    #
    # 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/#charfield
    session_key_hash = models.CharField(
        verbose_name='Хэш ключа сессии',
        max_length=64,                    # SHA-256 hex = 64 символа
        null=True,
        blank=True,
        db_index=True,
    )

    # is_active — флаг активности корзины.
    # True = корзина используется (можно добавлять/удалять товары).
    # False = корзина «мусорная» (оформлен заказ / слита с другой).
    # db_index=True — частый фильтр: Cart.objects.filter(is_active=True)
    # Без индекса: PostgreSQL сканирует ВСЮ таблицу при каждом запросе.
    #
    # ПОЧЕМУ НЕ УДАЛЯЕМ, А ДЕАКТИВИРУЕМ:
    #   1) Аналитика: «сколько корзин заброшено» → conversion rate
    #   2) Безопасность: если удалить → CartItem тоже каскадно удалятся
    #      → если заказ ссылался на item_id → битые ссылки
    #   3) Восстановление: пользователь может «вернуть» корзину
    is_active = models.BooleanField(
        verbose_name='Активна',
        default=True,
        db_index=True,
    )

    class Meta:
        # verbose_name — единственное число для Admin: «Корзина»
        # verbose_name_plural — множественное: «Корзины»
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/options/#verbose-name
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

        # ordering — сортировка ПО УМОЛЧАНИЮ для QuerySet.
        # '-created_at' = новые корзины первыми (DESC).
        # Используется в Admin и при Cart.objects.all().
        # Минус: ORDER BY добавляется ко ВСЕМ запросам → может замедлить.
        # Если нужен неупорядоченный запрос → Cart.objects.all().order_by()
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/options/#ordering
        ordering = ('-created_at',)

        # indexes — составные (multi-column) индексы.
        # Django автоматически создаёт индексы для FK (user) и db_index полей.
        # Но составные индексы нужно создавать вручную для частых комбинаций:
        #   WHERE user_id = X AND is_active = true
        #   WHERE session_key_hash = X AND is_active = true
        # PostgreSQL может использовать составной индекс вместо двух отдельных.
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/options/#indexes
        # 📖 https://www.postgresql.org/docs/current/indexes-multicolumn.html
        indexes = [
            # Составной индекс (user, is_active) — ускоряет:
            #   Cart.objects.get(user=X, is_active=True)
            # Индекс (user, is_active) также покрывает запросы
            # только по user (leftmost prefix rule).
            models.Index(
                fields=['user', 'is_active'],
                # name ≤ 30 символов! PostgreSQL limit для имён индексов.
                # cart_user_active_idx = 20 символов ✅
                name='cart_user_active_idx',
            ),
            # Составной индекс (session_key_hash, is_active) — ускоряет:
            #   Cart.objects.get(session_key_hash=X, is_active=True)
            models.Index(
                fields=['session_key_hash', 'is_active'],
                name='cart_session_active_idx',
            ),
        ]

        # constraints — ограничения целостности на уровне БД.
        # В отличие от Python-валидации (clean()), constraints
        # гарантируют целостность ВСЕГДА, даже при bulk_create,
        # raw SQL и прямых запросах к БД.
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/
        constraints = [
            # ── UniqueConstraint: одна активная корзина на юзера ──
            #
            # fields=['user'] — уникальность по полю user.
            # condition=Q(is_active=True) & Q(user__isnull=False) —
            #   условие partial uniqueness: ограничение применяется
            #   ТОЛЬКО когда is_active=True И user не NULL.
            #
            # Это позволяет:
            #   ✅ user=1, is_active=True  — только ОДНА такая запись
            #   ✅ user=1, is_active=False — СКОЛЬКО УГОДНО записей
            #   ✅ user=NULL               — не попадает под constraint
            #
            # 📖 https://www.postgresql.org/docs/current/indexes-partial.html
            models.UniqueConstraint(
                fields=['user'],
                # user__isnull=False — обязательно! Без этого:
                #   NULL = NULL → False в SQL → constraint не сработает.
                #   Но лучше перестраховаться — PostgreSQL может трактовать
                #   NULL по-разному в разных версиях.
                condition=Q(is_active=True) & Q(user__isnull=False),
                name='unique_active_user_cart',
            ),

            # ── UniqueConstraint: одна активная корзина на сессию ──
            # Аналогично user, но для гостевых корзин.
            models.UniqueConstraint(
                fields=['session_key_hash'],
                condition=Q(is_active=True) & Q(session_key_hash__isnull=False),
                name='unique_active_session_cart',
            ),

            # ── CheckConstraint: обязательно наличие владельца ──
            # Q(user__isnull=False) | Q(session_key_hash__isnull=False)
            # = «user НЕ NULL ИЛИ session_key_hash НЕ NULL»
            #
            # Без: можно создать Cart() без владельца → «сиротская» корзина
            # → никто к ней не имеет доступа → мусор в БД.
            #
            # 📖 https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint
            models.CheckConstraint(
        condition=Q(user__isnull=False) | Q(session_key_hash__isnull=False),
                name='cart_owner_required',
            ),
        ]

    # ----------------------------------------------------------
    # Утилиты
    # ----------------------------------------------------------

    @staticmethod
    def hash_session_key(session_key: str) -> str:
        """
        Возвращает SHA-256 хэш session_key в hex-формате.

        @staticmethod — не нужен self, можно вызывать:
          Cart.hash_session_key('abc123') — без создания экземпляра.

        АЛГОРИТМ:
          1. session_key.encode('utf-8') → bytes
          2. hashlib.sha256(bytes) → хэш-объект
          3. .hexdigest() → строка из 64 hex-символов

        ПОЧЕМУ SHA-256, А НЕ MD5:
          MD5 — 128 бит, уязвим к collision attacks.
          SHA-256 — 256 бит, криптографически стойкий.
          Мы не хэшируем пароли (для этого bcrypt/argon2),
          а просто защищаем session_key от утечки → SHA-256 достаточно.
          📖 https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
        """
        # encode('utf-8') — SHA-256 работает с bytes, не со строками.
        # UTF-8 — стандартная кодировка, session_key всегда ASCII,
        # но encode для безопасности.
        return hashlib.sha256(session_key.encode('utf-8')).hexdigest()

    # ----------------------------------------------------------
    # Представление (__str__)
    # ----------------------------------------------------------

    def __str__(self):
        """
        Человекочитаемое представление корзины.

        Используется в:
          • Django Admin (список корзин)
          • shell: Cart.objects.first() → «Корзина пользователя admin»
          • Логи: logger.info(f'Cart: {cart}')

        📖 https://docs.djangoproject.com/en/stable/ref/models/instances/#django.db.models.Model.__str__
        """
        if self.user_id:
            # self.user_id — FK id (integer), без дополнительного SQL.
            # self.user — доступ к объекту пользователя → SQL-запрос!
            # Поэтому проверяем user_id (уже загружен), а не user.
            return f'Корзина пользователя {self.user}'
        # Для гостевой корзины показываем первые 8 символов хэша.
        # [:8] — короткий идентификатор для отладки.
        short = self.session_key_hash[:8] if self.session_key_hash else '?'
        return f'Гостевая корзина {short}…'

    # ----------------------------------------------------------
    # Валидация
    # ----------------------------------------------------------

    def clean(self):
        """
        Python-уровневая валидация модели.

        Дублирует CheckConstraint cart_owner_required — но на уровне Python.
        Зачем дублировать:
          • CheckConstraint → IntegrityError при save() (некрасиво в формах)
          • clean() → ValidationError с дружелюбным сообщением
          • Админка и формы вызывают clean() автоматически → красивая ошибка
          • bulk_create / raw SQL обходят clean() → constraint защищает

        ВАЖНО: full_clean() НЕ вызывается автоматически в save()!
        Почему: это замедлило бы bulk-операции и конфликтовало бы
        с валидацией сериализаторов DRF.
        📖 https://docs.djangoproject.com/en/stable/ref/models/instances/#django.db.models.Model.clean
        """
        # super().clean() — вызываем родительскую валидацию BaseModel.
        # BaseModel.clean() — нет (он не переопределён), но привычка
        # вызывать super() защищает от будущих изменений.
        super().clean()
        # Проверяем что ХОТЯ БЫ один владелец указан.
        if not self.user_id and not self.session_key_hash:
            raise ValidationError(
                'Необходимо указать user или session_key_hash.'
            )

    # NB: full_clean() в save() намеренно НЕ вызываем —
    # это дублирует валидацию форм/сериализаторов и ломает bulk-операции.
    # Целостность гарантирована на уровне БД через CheckConstraint.
