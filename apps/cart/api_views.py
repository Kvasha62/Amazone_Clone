from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Cart, CartItem

from apps.catalog.models import ProductVariant

from .serializers import CartSerializer


# 🛒 Получение корзины
class CartAPIView(APIView):

    def get_cart(self, request):

        # Авторизованный пользователь
        if request.user.is_authenticated:

            cart, created = Cart.objects.get_or_create(
                user=request.user,
                is_active=True
            )

            return cart

        # Guest cart
        session_key = request.session.session_key

        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart, created = Cart.objects.get_or_create(
            session_key=session_key,
            is_active=True
        )

        return cart

    # GET
    def get(self, request):

        cart = self.get_cart(request)

        serializer = CartSerializer(cart)

        return Response(serializer.data)

    # POST
    def post(self, request):

        cart = self.get_cart(request)

        variant_id = request.data.get('variant_id')

        quantity = int(request.data.get('quantity', 1))

        variant = ProductVariant.objects.get(id=variant_id)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )

        # Если товар уже есть
        if not created:
            item.quantity += quantity
            item.save()

        serializer = CartSerializer(cart)

        return Response(serializer.data, status=status.HTTP_201_CREATED)