import hashlib

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.cart.managers.cart_manager import CartManager

User = get_user_model()


# ==========================================================
# КОРЗИНА
# ==========================================================

class Cart(BaseModel):
    """
    Корзина пользователя.

    Может принадлежать:
      - авторизованному пользователю (user)
      - гостю (session_key_hash — SHA-256 хэш ключа сессии;
        храним хэш, а не исходный ключ, чтобы при компрометации БД
        нельзя было подменить сессию).

    Инварианты:
      - У одного юзера / одного session_key одновременно
        может быть только ОДНА активная корзина (UniqueConstraint).
      - Должен быть указан либо user, либо session_key_hash
        (CheckConstraint).
    """

    objects = CartManager()

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name='Пользователь',
    )

    # Храним хэш session_key, а не сам ключ — защита от утечки сессий
    # в случае компрометации БД. Алгоритм — SHA-256.
    session_key_hash = models.CharField(
        verbose_name='Хэш ключа сессии',
        max_length=64,                    # длина sha256 в hex
        null=True,
        blank=True,
        db_index=True,
    )

    is_active = models.BooleanField(
        verbose_name='Активна',
        default=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        ordering = ('-created_at',)

        # db_index=True на полях user / session_key_hash / is_active
        # Django уже создаёт автоматически. Оставляем только составные.
        indexes = [
            models.Index(
                fields=['user', 'is_active'],
                name='cart_user_active_idx',
            ),
            models.Index(
                fields=['session_key_hash', 'is_active'],
                name='cart_session_active_idx',
            ),
        ]

        constraints = [
            # Только одна активная корзина у юзера
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_active=True) & Q(user__isnull=False),
                name='unique_active_user_cart',
            ),
            # Только одна активная корзина у гостя
            models.UniqueConstraint(
                fields=['session_key_hash'],
                condition=Q(is_active=True) & Q(session_key_hash__isnull=False),
                name='unique_active_session_cart',
            ),
            # Должен быть владелец: либо user, либо session_key_hash
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
        """Возвращает SHA-256 хэш session_key в hex-формате."""
        return hashlib.sha256(session_key.encode('utf-8')).hexdigest()

    # ----------------------------------------------------------
    # Представление
    # ----------------------------------------------------------

    def __str__(self):
        if self.user_id:
            return f'Корзина пользователя {self.user}'
        short = self.session_key_hash[:8] if self.session_key_hash else '?'
        return f'Гостевая корзина {short}…'

    # ----------------------------------------------------------
    # Валидация
    # ----------------------------------------------------------

    def clean(self):
        """
        Дублируем CheckConstraint на уровне Python — чтобы давать
        дружелюбное сообщение в формах/админке вместо IntegrityError.
        """
        super().clean()
        if not self.user_id and not self.session_key_hash:
            raise ValidationError(
                'Необходимо указать user или session_key_hash.'
            )

    # NB: full_clean() в save() намеренно НЕ вызываем —
    # это дублирует валидацию форм/сериализаторов и ломает bulk-операции.
    # Целостность гарантирована на уровне БД через CheckConstraint.
