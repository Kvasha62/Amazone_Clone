from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'channel', 'title', 'body',
            'status', 'related_object_type', 'related_object_id',
            'action_url', 'is_read', 'sent_at', 'read_at', 'created_at',
        )
        read_only_fields = fields


class NotificationListSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'title', 'status',
            'is_read', 'created_at',
        )
        read_only_fields = fields
