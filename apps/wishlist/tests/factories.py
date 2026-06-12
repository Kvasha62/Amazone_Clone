from apps.catalog.tests.factories import CatalogTestCase
from apps.wishlist.models import Wishlist, WishlistItem


def create_test_wishlist(user):
    """Создаёт тестовый список желаний."""
    return Wishlist.objects.create(user=user)


def create_test_wishlist_item(wishlist, variant, *, note=''):
    """Создаёт тестовую позицию в списке желаний."""
    return WishlistItem.objects.create(
        wishlist=wishlist,
        variant=variant,
        note=note,
    )
