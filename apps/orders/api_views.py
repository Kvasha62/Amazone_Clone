from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import (
    Order,
    OrderItem
)

from .serializers import OrderSerializer

from apps.cart.models import Cart


# 🛒 Checkout
class CheckoutAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        # Получаем корзину пользователя
        cart = Cart.objects.get(
            user=request.user,
            is_active=True
        )

        # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            shipping_address=request.data.get(
                'shipping_address'
            )
        )

        # Перенос товаров
        for item in cart.items.all():

            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                price=item.variant.price.price,
                quantity=item.quantity
            )

            # 🔥 Уменьшаем склад
            stock = item.variant.stock

            stock.quantity -= item.quantity

            stock.save()

        # Пересчет суммы
        order.calculate_total()

        # Очищаем корзину
        cart.items.all().delete()

        serializer = OrderSerializer(order)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


# 📦 История заказов
class OrderListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        orders = Order.objects.filter(
            user=request.user
        )

        serializer = OrderSerializer(
            orders,
            many=True
        )

        return Response(serializer.data)
