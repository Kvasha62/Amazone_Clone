# ────────────────────────────────────────────────────────────────────────
# apps/cart/management/commands/cleanup_expired_carts.py
#
# Management-команда для очистки устаревших корзин.
#
# ДВА ДЕЙСТВИЯ (через CartService.cleanup_expired_carts — PROD-002):
#   1. Удаляет неактивные корзины, не обновлявшиеся > CART_INACTIVE_TTL_DAYS
#   2. Помечает как неактивные гостевые корзины, не обновлявшиеся
#      > CART_GUEST_STALE_DAYS (брошенные корзины)
#
# ЗАПУСК:
#   python manage.py cleanup_expired_carts
#   python manage.py cleanup_expired_carts --dry-run
#   python manage.py cleanup_expired_carts --inactive-days=60
#   python manage.py cleanup_expired_carts --guest-stale-days=21
#
# 📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
# ────────────────────────────────────────────────────────────────────────

from django.core.management.base import BaseCommand

from apps.cart.constants import CART_INACTIVE_TTL_DAYS, CART_GUEST_STALE_DAYS
from apps.cart.services.cart_service import CartService


class Command(BaseCommand):
    """Management-команда для очистки устаревших корзин."""

    help = (
        'Удаляет неактивные корзины старше CART_INACTIVE_TTL_DAYS '
        'и помечает неактивными брошенные гостевые корзины.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Показать что будет удалено, без реального удаления.',
        )
        parser.add_argument(
            '--inactive-days',
            type=int,
            default=CART_INACTIVE_TTL_DAYS,
            help=f'Дней до удаления неактивных корзин (по умолчанию {CART_INACTIVE_TTL_DAYS}).',
        )
        parser.add_argument(
            '--guest-stale-days',
            type=int,
            default=CART_GUEST_STALE_DAYS,
            help=f'Дней до деактивации гостевых корзин (по умолчанию {CART_GUEST_STALE_DAYS}).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        inactive_days = options['inactive_days']
        guest_stale_days = options['guest_stale_days']

        result = CartService.cleanup_expired_carts(
            inactive_days=inactive_days,
            guest_stale_days=guest_stale_days,
            dry_run=dry_run,
        )

        inactive_cutoff = result['inactive_cutoff']
        guest_cutoff = result['guest_cutoff']
        inactive_candidates = result['inactive_candidates']
        guest_candidates = result['guest_candidates']

        if inactive_candidates:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Будет удалено {inactive_candidates} '
                        f'неактивных корзин (updated_at < {inactive_cutoff.date()}).'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Удалено {result["inactive_deleted"]} неактивных корзин '
                        f'(updated_at < {inactive_cutoff.date()}).'
                    )
                )
        else:
            self.stdout.write('Нет неактивных корзин для удаления.')

        if guest_candidates:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Будет деактивировано {guest_candidates} '
                        f'гостевых корзин (updated_at < {guest_cutoff.date()}).'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Деактивировано {result["guest_deactivated"]} гостевых корзин '
                        f'(updated_at < {guest_cutoff.date()}).'
                    )
                )
        else:
            self.stdout.write('Нет брошенных гостевых корзин.')

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Изменения НЕ применены.'))
