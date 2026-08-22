# ────────────────────────────────────────────────────────────────────────
# apps/inventory/management/commands/check_low_stock.py —
# Management-команда для проверки товаров с низким остатком.
#
# ВЫЗОВ:
#   python manage.py check_low_stock
#   python manage.py check_low_stock --threshold 10
#   python manage.py check_low_stock --json
#
# Crontab (рекомендация):
#   0 9 * * * cd /app && python manage.py check_low_stock >> /var/log/low_stock.log 2>&1
#   → каждый день в 9:00
#
# 📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Нет автоматической проверки «мало товара»
#   • Менеджер склада не узнает что нужно пополнить
# ────────────────────────────────────────────────────────────────────────

import json

from django.core.management.base import BaseCommand

from apps.inventory.models import Stock


class Command(BaseCommand):
    help = 'Показывает товары с низким остатком на складе.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=None,
            help='Порог для фильтра (переопределяет low_stock_threshold варианта).',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            default=False,
            help='Вывести результат в JSON формате.',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        use_json = options['json']

        if threshold is not None:
            # Глобальный порог — игнорируем индивидуальный.
            low_stocks = Stock.objects.filter(
                quantity__lte=threshold,
                quantity__gt=0,
            ).with_variant()
        else:
            # Индивидуальный порог каждого варианта.
            low_stocks = Stock.objects.low_stock().with_variant()

        count = low_stocks.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ Все товары в наличии.'))
            return

        self.stdout.write(f'⚠️  Найдено {count} товаров с низким остатком:\n')

        results = []
        for stock in low_stocks:
            sku = getattr(stock.variant, 'sku', '???')
            product = getattr(
                getattr(stock.variant, 'product', None), 'name', '???',
            )
            line = (
                f'  {sku} ({product}): '
                f'{stock.quantity} шт. '
                f'(порог: {stock.low_stock_threshold})'
            )
            self.stdout.write(line)

            results.append({
                'sku': sku,
                'product': product,
                'quantity': stock.quantity,
                'threshold': stock.low_stock_threshold,
                'available': stock.available_quantity,
            })

        if use_json:
            self.stdout.write('\n--- JSON ---')
            self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

        self.stdout.write(self.style.WARNING(
            f'\nИтого: {count} товаров требуют пополнения.',
        ))
