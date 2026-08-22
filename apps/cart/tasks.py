# ────────────────────────────────────────────────────────────────────────
# apps/cart/tasks.py — Celery-задачи для корзины.
#
# Фоновые задачи:
#   - cleanup_old_carts    — очистка неактивных корзин (каждый день)
#   - send_abandoned_cart_reminders — email-напоминания (каждый час)
# ────────────────────────────────────────────────────────────────────────

from celery import shared_task
from django.utils import timezone


@shared_task(name='apps.cart.tasks.cleanup_old_carts')
def cleanup_old_carts():
    """
    Очистка старых корзин.
    Вызывает management-команду cleanup_expired_carts через Django API.
    """
    from django.core.management import call_command
    call_command('cleanup_expired_carts')


@shared_task(name='apps.cart.tasks.send_abandoned_cart_reminders')
def send_abandoned_cart_reminders():
    """
    Отправка напоминаний о брошенных корзинах.
    Пока заглушка — будет реализовано при интеграции с email.
    """
    from apps.cart.models import Cart
    from datetime import timedelta

    threshold = timezone.now() - timedelta(hours=24)
    abandoned = Cart.objects.filter(
        is_active=True,
        updated_at__lt=threshold,
        user__isnull=False,
    ).select_related('user')

    count = abandoned.count()
    if count > 0:
        # TODO: отправить email через apps.notifications.services
        pass

    return f'Найдено {count} брошенных корзин'
