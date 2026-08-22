# ────────────────────────────────────────────────────────────────────────
# apps/cart/management/commands/cleanup_expired_carts.py
#
# Management-команда для очистки устаревших корзин.
#
# ДВА ДЕЙСТВИЯ:
#   1. Удаляет неактивные корзины, не обновлявшиеся > CART_INACTIVE_TTL_DAYS
#   2. Помечает как неактивные гостевые корзины, не обновлявшиеся
#      > CART_GUEST_STALE_DAYS (брошенные корзины)
#
# ЗАПУСК:
#   python manage.py cleanup_expired_carts
#   python manage.py cleanup_expired_carts --dry-run       # показать, не удалять
#   python manage.py cleanup_expired_carts --inactive-days=60
#   python manage.py cleanup_expired_carts --guest-stale-days=21
#
# CRON (рекомендуется):
#   0 3 * * * cd /app && python manage.py cleanup_expired_carts >> /var/log/cleanup.log 2>&1
#   Запуск каждый день в 3:00 ночи — минимальная нагрузка.
#
# 📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#delete
# 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#update
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • python manage.py cleanup_expired_carts → Unknown command
#   • Корзины будут накапливаться бесконечно → таблица разрастётся
# ────────────────────────────────────────────────────────────────────────

# timedelta — для вычисления даты «N дней назад».
# 📖 https://docs.python.org/3/library/datetime.html#datetime.timedelta
from datetime import timedelta

# BaseCommand — базовый класс для management-команд.
# 📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/#django.core.management.base.BaseCommand
from django.core.management.base import BaseCommand

# timezone — Django обёртка над datetime с поддержкой USE_TZ.
# timezone.now() → datetime с timezone (если USE_TZ=True).
# 📖 https://docs.djangoproject.com/en/stable/ref/utils/#django.utils.timezone
from django.utils import timezone

# Константы TTL из модуля корзины.
from apps.cart.constants import CART_INACTIVE_TTL_DAYS, CART_GUEST_STALE_DAYS

# Cart — модель корзины.
from apps.cart.models import Cart


class Command(BaseCommand):
    """
    Management-команда для очистки устаревших корзин.

    help — текст, который отображается при:
      python manage.py help cleanup_expired_carts
    """
    help = (
        'Удаляет неактивные корзины старше CART_INACTIVE_TTL_DAYS '
        'и помечает неактивными брошенные гостевые корзины.'
    )

    def add_arguments(self, parser):
        """
        Определение аргументов командной строки.

        parser — argparse.ArgumentParser (стандартная библиотека Python).
        📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/#accepting-optional-arguments
        """
        # --dry-run — флаг (action='store_true').
        # Если передан → dry_run=True, иначе → dry_run=False.
        # Показать что будет удалено, БЕЗ реального удаления.
        parser.add_argument(
            '--dry-run',
            action='store_true',    # Флаг: --dry-run → True
            dest='dry_run',         # Имя в options dict
            help='Показать что будет удалено, без реального удаления.',
        )
        # --inactive-days — кастомный TTL для удаления неактивных.
        # По умолчанию = CART_INACTIVE_TTL_DAYS (30).
        parser.add_argument(
            '--inactive-days',
            type=int,
            default=CART_INACTIVE_TTL_DAYS,
            help=f'Дней до удаления неактивных корзин (по умолчанию {CART_INACTIVE_TTL_DAYS}).',
        )
        # --guest-stale-days — кастомный TTL для деактивации гостевых.
        # По умолчанию = CART_GUEST_STALE_DAYS (14).
        parser.add_argument(
            '--guest-stale-days',
            type=int,
            default=CART_GUEST_STALE_DAYS,
            help=f'Дней до деактивации гостевых корзин (по умолчанию {CART_GUEST_STALE_DAYS}).',
        )

    def handle(self, *args, **options):
        """
        Основная логика команды.

        options — словарь с аргументами:
          options['dry_run'] = True/False
          options['inactive_days'] = int
          options['guest_stale_days'] = int
        """
        # Распаковываем аргументы.
        dry_run = options['dry_run']
        inactive_days = options['inactive_days']
        guest_stale_days = options['guest_stale_days']

        # Вычисляем пороговые даты.
        # now = 2026-06-12 03:00:00 UTC (пример)
        # inactive_cutoff = now - 30 дней = 2026-05-13 03:00:00 UTC
        # Корзины с updated_at < inactive_cutoff → кандидаты на удаление.
        now = timezone.now()
        inactive_cutoff = now - timedelta(days=inactive_days)
        guest_cutoff = now - timedelta(days=guest_stale_days)

        # ----------------------------------------------------------
        # 1. Удаление старых неактивных корзин
        # ----------------------------------------------------------

        # Ищем неактивные корзины, не обновлявшиеся дольше TTL.
        # is_active=False → корзина была деактивирована (merge / order)
        # updated_at__lt=inactive_cutoff → старше TTL
        old_inactive = Cart.objects.filter(
            is_active=False,
            updated_at__lt=inactive_cutoff,
        )
        # .count() — SELECT COUNT(*) — быстрый запрос для подсчёта.
        old_inactive_count = old_inactive.count()

        if old_inactive_count:
            if dry_run:
                # dry_run → показываем что будет удалено.
                # self.style.WARNING — жёлтый цвет в терминале.
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Будет удалено {old_inactive_count} '
                        f'неактивных корзин (updated_at < {inactive_cutoff.date()}).'
                    )
                )
            else:
                # .delete() — DELETE FROM cart_cart WHERE ...
                # Возвращает кортеж (total_deleted, {model: count}).
                # CartItem удаляется КАСКАДНО (on_delete=CASCADE на Cart.cart).
                # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#delete
                deleted_count, deleted_details = old_inactive.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Удалено {old_inactive_count} неактивных корзин '
                        f'(updated_at < {inactive_cutoff.date()}). '
                        f'Детали: {deleted_details}'
                    )
                )
        else:
            self.stdout.write('Нет неактивных корзин для удаления.')

        # ----------------------------------------------------------
        # 2. Деактивация брошенных гостевых корзин
        # ----------------------------------------------------------

        # Ищем АКТИВНЫЕ гостевые корзины, не обновлявшиеся дольше TTL.
        # is_active=True → корзина ещё «живая»
        # user__isnull=True → гостевая (нет привязки к пользователю)
        # updated_at__lt=guest_cutoff → старше TTL
        stale_guest = Cart.objects.filter(
            is_active=True,
            user__isnull=True,
            updated_at__lt=guest_cutoff,
        )
        stale_guest_count = stale_guest.count()

        if stale_guest_count:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Будет деактивировано {stale_guest_count} '
                        f'гостевых корзин (updated_at < {guest_cutoff.date()}).'
                    )
                )
            else:
                # .update(is_active=False) — один SQL:
                # UPDATE cart_cart SET is_active = False WHERE id IN (...)
                # Не загружает объекты в Python — эффективно.
                # 📖 https://docs.djangoproject.com/en/stable/ref/models/querysets/#update
                updated = stale_guest.update(is_active=False)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Деактивировано {updated} гостевых корзин '
                        f'(updated_at < {guest_cutoff.date()}).'
                    )
                )
        else:
            self.stdout.write('Нет брошенных гостевых корзин.')

        # Итого: финальное сообщение для dry-run.
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Изменения НЕ применены.'))
