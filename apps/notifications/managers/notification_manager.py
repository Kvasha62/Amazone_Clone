# ────────────────────────────────────────────────────────────────────────
# apps/notifications/managers/notification_manager.py
#
# Использует from_queryset для автоматического наследования всех
# методов из NotificationQuerySet.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
# ────────────────────────────────────────────────────────────────────────

from django.db import models


class NotificationQuerySet(models.QuerySet):
    """
    Расширенный QuerySet для Notification.

    Методы:
      for_user(user)           — уведомления пользователя
      unread()                 — непрочитанные
      read()                   — прочитанные
      by_type(type)            — по типу уведомления
      by_channel(channel)      — по каналу (in_app, email, push)
      pending()                — ожидающие отправки
    """

    def for_user(self, user):
        return self.filter(user=user)

    def unread(self):
        """Непрочитанные (read_at IS NULL)."""
        return self.filter(read_at__isnull=True)

    def read(self):
        """Прочитанные (read_at IS NOT NULL)."""
        return self.filter(read_at__isnull=False)

    def by_type(self, notification_type):
        return self.filter(notification_type=notification_type)

    def by_channel(self, channel):
        return self.filter(channel=channel)

    def pending(self):
        return self.filter(status='pending')


# from_queryset автоматически копирует все методы QuerySet
# в Manager: for_user, unread, read, by_type, by_channel, pending
NotificationManager = models.Manager.from_queryset(NotificationQuerySet)
