# ────────────────────────────────────────────────────────────────────────
# apps/shipping/management/commands/cleanup_stale_shipments.py —
#   деактивация зависших отправлений.
#
# Отправления в статусе PREPARING, которые не были переданы
# в службу доставки дольше SHIPMENT_STALE_HOURS часов,
# переводятся в статус RETURNED через ShippingService (PROD-002).
#
# ЗАПУСК:
#   python manage.py cleanup_stale_shipments
#   python manage.py cleanup_stale_shipments --hours=72
#   python manage.py cleanup_stale_shipments --dry-run
#
# 📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
# ────────────────────────────────────────────────────────────────────────

import logging

from django.core.management.base import BaseCommand

from apps.shipping.services.shipping_service import ShippingService

logger = logging.getLogger(__name__)

DEFAULT_STALE_HOURS = 48


class Command(BaseCommand):
    help = (
        'Переводит зависшие отправления (PREPARING > N часов) '
        'в статус RETURNED.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=DEFAULT_STALE_HOURS,
            help=(
                f'Количество часов без обновления для считания '
                f'отправления «зависшим». По умолчанию: {DEFAULT_STALE_HOURS}.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Показать что будет изменено, но не применять.',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']

        result = ShippingService.return_stale_preparing(
            hours=hours,
            dry_run=dry_run,
        )
        count = result['candidates']

        if count == 0:
            self.stdout.write(
                f'Нет зависших отправлений (PREPARING > {hours}ч).'
            )
            return

        if dry_run:
            self.stdout.write(
                f'[DRY RUN] Будет переведено в RETURNED: {count} '
                f'отправлений (PREPARING > {hours}ч).'
            )
            for s in result['shipments'][:10]:
                self.stdout.write(f'  • {s.internal_tracking}')
            if count > 10:
                self.stdout.write(f'  ... и ещё {count - 10}')
            self.stdout.write('[DRY RUN] Изменения НЕ применены.')
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Переведено в RETURNED: {result["updated"]} зависших отправлений.'
            )
        )
