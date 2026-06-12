from django.contrib import admin
from apps.wishlist.models import Wishlist, WishlistItem


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'items_count', 'created_at', 'updated_at')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'wishlist', 'variant', 'note', 'created_at')
    raw_id_fields = ('wishlist', 'variant')
    ordering = ('-created_at',)
