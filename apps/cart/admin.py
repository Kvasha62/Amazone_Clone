from django.contrib import admin

from apps.cart.models import Cart,CartItem

admin.site.register(Cart)
admin.site.register(CartItem)
# Register your models here.
