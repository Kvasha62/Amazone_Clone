from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .serializers import PaymentSerializer
from .services.fake import FakePaymentGateway


class PaymentPayAPIView(APIView):
    """
    Тестовая оплата заказа.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):

        payment = Payment.objects.get(
            id=payment_id
        )

        payment = FakePaymentGateway.pay(payment)

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class PaymentFailAPIView(APIView):
    """
    Имитация ошибки оплаты.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):

        payment = Payment.objects.get(
            id=payment_id
        )

        payment = FakePaymentGateway.fail(payment)

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class PaymentRefundAPIView(APIView):
    """
    Имитация возврата денег.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):

        payment = Payment.objects.get(
            id=payment_id
        )

        payment = FakePaymentGateway.refund(payment)

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
