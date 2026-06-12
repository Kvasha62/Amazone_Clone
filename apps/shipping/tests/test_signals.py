# ────────────────────────────────────────────────────────────────────────
# apps/shipping/tests/test_signals.py — тесты сигналов модуля доставки.
#
# Проверяет:
#   • on_shipment_created — логирование при создании
#
# 📖 https://docs.djangoproject.com/en/stable/topics/testing/overview/
# ────────────────────────────────────────────────────────────────────────

import logging
import logging.handlers
from decimal import Decimal

from django.test import TestCase

from apps.orders.tests.factories import create_test_order, create_test_user
from apps.shipping.tests.factories import create_test_shipment


class ShipmentSignalTests(TestCase):
    """Тесты сигналов отправлений."""

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(self.user, status='confirmed')

    def test_signal_fires_on_create(self):
        """Сигнал on_shipment_saved вызывается при создании."""
        with self.assertLogs('apps.shipping.signals', level='INFO') as cm:
            create_test_shipment(self.order)

        # Должен быть лог 'shipment_created_signal'
        log_messages = '\n'.join(cm.output)
        self.assertIn('shipment_created_signal', log_messages)

    def test_signal_not_on_update(self):
        """Сигнал не пишет лог shipment_created_signal при обновлении."""
        shipment = create_test_shipment(self.order)

        # Используем handler с логгером для отслеживания вызовов.
        import logging
        test_handler = logging.handlers.MemoryHandler(capacity=100)
        logger = logging.getLogger('apps.shipping.signals')
        logger.addHandler(test_handler)
        original_level = logger.level
        logger.setLevel(logging.DEBUG)

        try:
            shipment.tracking_number = 'UPD-123'
            shipment.save()

            # Проверяем что shipment_created_signal НЕ появился в логах
            log_messages = [
                r.getMessage() for r in test_handler.buffer
            ]
            for msg in log_messages:
                self.assertNotIn('shipment_created_signal', msg)
        finally:
            logger.removeHandler(test_handler)
            logger.setLevel(original_level)
