# ────────────────────────────────────────────────────────────────────────
# apps/orders/signals.py — Django-сигналы для модуля заказов.
#
# СИГНАЛЫ — механизм callback'ов Django: при определённых событиях
# (save, delete, m2m_changed) автоматически вызываются обработчики.
#
# НАЗНАЧЕНИЕ:
#   1. post_save Order (created) — логирование создания заказа
#   2. post_save Order (!created) — логирование изменения заказа
#
# ПОЧЕМУ НЕ ВСЯ ЛОГИКА В save():
#   • Сигналы срабатывают ВСЕГДА: save(), bulk_update(), admin, shell
#   • save() можно обойти через bulk_create() / querysets.update()
#   • Сигналы — «последний рубеж» для side-effects
#
# ОСТОРОЖНО:
#   • Сигналы выполняются СИНХРОННО — тяжёлые операции замедляют save()
#   • Для email/push — использовать Celery (background task)
#   • Не делать в сигналах то, что можно сделать в сервисе
#
# ПОЧЕМУ __import__() ДЛЯ КОДИРОВАНИЯ:
#   Если signals.py импортирует models.py на верхнем уровне →
#   circular import (models → signals → models).
#   __import__() + lazy loading внутри функции — безопасно.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#post-save
# 📖 https://docs.djangoproject.com/en/stable/topics/signals/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Логирование создания/изменения заказов не работает
#   • Уведомления не отправляются (если добавлены)
#   • Аналитика неполная
# ────────────────────────────────────────────────────────────────────────

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='orders.Order')
def on_order_saved(sender, instance, created, **kwargs):
    """
    Обработчик post_save для Order.

    ВЫЗЫВАЕТСЯ:
      • created=True — при первом save() (создание заказа)
      • created=False — при последующих save() (обновление)

    ЧТО ДЕЛАЕТ:
      • created → логирует создание заказа (INFO)
      • !created → логирует обновление (DEBUG)

    РАСШИРЕНИЕ (будущие итерации):
      • Отправка email-уведомления при CONFIRMED
      • Push-уведомление при SHIPPED/DELIVERED
      • Интеграция с WMS (Warehouse Management System)

    ПОЧЕМУ НЕ ОТПРАВЛЯЕМ EMAIL ЗДЕСЬ:
      Email-отправка может занимать 1-5 секунд (SMTP handshake).
      В синхронном сигнале это заблокирует save() → API timeout.
      Решение: Celery task → delay() → отправка в фоне.
      📖 https://docs.celeryq.dev/en/stable/

    sender='orders.Order' — строковая ссылка (lazy).
    Без строки: from apps.orders.models import Order → circular import risk.
    📖 https://docs.djangoproject.com/en/stable/ref/signals/#post-save
    """
    if created:
        logger.info(
            'order_created_signal',
            extra={
                'order_id': instance.pk,
                'order_number': instance.order_number,
                'user_id': instance.user_id,
                'status': instance.status,
                'total': str(instance.total),
            },
        )
    else:
        logger.debug(
            'order_updated_signal',
            extra={
                'order_id': instance.pk,
                'order_number': instance.order_number,
                'status': instance.status,
            },
        )
