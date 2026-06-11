import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.cart.services.cart_service import CartService

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    """
    При логине через session-авторизацию переносим гостевую корзину
    в пользовательскую.

    ВНИМАНИЕ: этот сигнал НЕ срабатывает при JWT / Token-авторизации.
    Для JWT используйте POST /api/v1/cart/merge/ (CartMergeView).
    """
    session_key = request.session.session_key
    if not session_key:
        logger.debug('cart_merge_skip: no session_key at login')
        return

    result = CartService.merge_guest_into_user_cart(session_key, user)
    if result:
        logger.info('cart_merged_on_login', extra={'user_id': user.pk})
