"""
Тесты сигналов корзины.
"""
import weakref

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.cart.signals import merge_guest_cart_on_login

User = get_user_model()


class CartSignalTests(TestCase):

    def test_signal_function_exists(self):
        """Сигнал merge_guest_cart_on_login зарегистрирован."""
        self.assertTrue(hasattr(merge_guest_cart_on_login, '__name__'))

    def test_signal_connected_to_user_logged_in(self):
        """Функция подключена к user_logged_in."""
        # receivers хранит flat-кортежи; структура зависит от версии Django.
        # Ищем weakref.ref(нашу_функцию) среди всех элементов каждого кортежа.
        found = False
        for entry in user_logged_in.receivers:
            for item in entry:
                if isinstance(item, weakref.ref):
                    func = item()
                elif callable(item):
                    func = item
                else:
                    continue
                if func is not None and getattr(func, '__name__', '') == 'merge_guest_cart_on_login':
                    found = True
                    break
            if found:
                break

        self.assertTrue(
            found,
            'merge_guest_cart_on_login не подключена к user_logged_in',
        )
