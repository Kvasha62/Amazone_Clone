from django.urls import path
from apps.wishlist.api_views import (
    WishlistAddView,
    WishlistClearView,
    WishlistListView,
    WishlistMoveToCartView,
    WishlistRemoveView,
)

app_name = 'wishlist'

urlpatterns = [
    path('', WishlistListView.as_view(), name='wishlist-detail'),
    path('add/', WishlistAddView.as_view(), name='wishlist-add'),
    path('remove/<int:item_id>/', WishlistRemoveView.as_view(), name='wishlist-remove'),
    path('move-to-cart/', WishlistMoveToCartView.as_view(), name='wishlist-move-to-cart'),
    path('clear/', WishlistClearView.as_view(), name='wishlist-clear'),
]
