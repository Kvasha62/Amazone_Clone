# apps/payments/services/fake.py

from uuid import uuid4

from apps.payments.models import Payment


class FakePaymentGateway:
    """
    Тестовый платежный шлюз.

    Используется во время разработки проекта.
    Вместо реального списания денег
    просто меняет статус платежа.
    """

    @staticmethod
    def create_payment(payment: Payment) -> dict:
        """
        Создание платежа.

        В реальной системе здесь будет запрос
        в ЮKassa или Т-Банк.
        """

        # Генерируем тестовый идентификатор платежа
        payment.provider_payment_id = f"FAKE-{uuid4()}"

        payment.save()

        return {
            "payment_id": payment.provider_payment_id,
            "status": payment.status,
            "payment_url": (
                f"/api/payments/{payment.id}/pay/"
            )
        }

    @staticmethod
    def pay(payment: Payment) -> Payment:
        """
        Имитация успешной оплаты.
        """

        payment.status = Payment.STATUS_PAID

        payment.save()

        # Меняем статус заказа
        order = payment.order

        order.status = "paid"

        order.save()

        return payment

    @staticmethod
    def fail(payment: Payment) -> Payment:
        """
        Имитация ошибки оплаты.
        """

        payment.status = Payment.STATUS_FAILED

        payment.save()

        return payment

    @staticmethod
    def refund(payment: Payment) -> Payment:
        """
        Имитация возврата средств.
        """

        payment.status = Payment.STATUS_REFUNDED

        payment.save()

        return payment