from django.contrib import admin
from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'notification_type', 'channel',
        'title', 'status', 'sent_at', 'read_at',
    )
    list_filter = ('notification_type', 'channel', 'status')
    search_fields = ('title', 'body')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)
    list_per_page = 50
