# ────────────────────────────────────────────────────────────────────────
# apps/notifications/models/notification.py — уведомление пользователя.
#
# Единая модель для всех типов уведомлений:
#   in_app, email, push.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/
# ────────────────────────────────────────────────────────────────────────

from django.conf import settings
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.notifications.constants import (
    CHANNEL_CHOICES,
    CHANNEL_IN_APP,
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    NOTIFICATION_TYPE_CHOICES,
    STATUS_CHOICES,
    STATUS_PENDING,
)
from apps.notifications.managers.notification_manager import NotificationManager


class Notification(BaseModel):
    """
    Уведомление пользователя.

    Хранит все уведомления: in-app, email, push.
    Для in-app — есть статус прочитанности (read_at).

    СВЯЗИ:
      • User (FK) — получатель уведомления
    """

    objects = NotificationManager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Пользователь',
    )

    notification_type = models.CharField(
        verbose_name='Тип',
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True,
    )

    channel = models.CharField(
        verbose_name='Канал',
        max_length=10,
        choices=CHANNEL_CHOICES,
        default=CHANNEL_IN_APP,
        db_index=True,
    )

    title = models.CharField(
        verbose_name='Заголовок',
        max_length=MAX_TITLE_LENGTH,
    )

    body = models.TextField(
        verbose_name='Текст',
        max_length=MAX_BODY_LENGTH,
        blank=True,
        default='',
    )

    status = models.CharField(
        verbose_name='Статус',
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # Связанный объект (опционально)
    # Примеры: order_id, shipment_id, review_id
    related_object_type = models.CharField(
        verbose_name='Тип связанного объекта',
        max_length=50,
        blank=True,
        default='',
    )
    related_object_id = models.PositiveIntegerField(
        verbose_name='ID связанного объекта',
        null=True,
        blank=True,
    )

    # URL для перехода (опционально)
    action_url = models.URLField(
        verbose_name='URL действия',
        blank=True,
        default='',
    )

    # Когда отправлено
    sent_at = models.DateTimeField(
        verbose_name='Дата отправки',
        null=True,
        blank=True,
    )

    # Когда прочитано (in-app)
    read_at = models.DateTimeField(
        verbose_name='Дата прочтения',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ('-created_at',)
        indexes = [
            models.Index(
                fields=['user', 'status'],
                name='notif_user_status_idx',
            ),
            models.Index(
                fields=['user', 'read_at'],
                name='notif_user_read_idx',
            ),
        ]

    def __str__(self):
        return f'Notif({self.user_id}, {self.notification_type}, {self.status})'

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
