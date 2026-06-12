from django.contrib import admin
from apps.discounts.models import Campaign, Coupon


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'started_at', 'ended_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('-created_at',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_type', 'discount_value',
        'is_active', 'times_used', 'max_total_uses',
        'started_at', 'ended_at',
    )
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code', 'description')
    raw_id_fields = ('campaign',)
    list_per_page = 50
    ordering = ('-created_at',)
