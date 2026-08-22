from django.urls import path
from apps.notifications.api_views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
    NotificationUnreadListView,
)

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread/', NotificationUnreadListView.as_view(), name='notification-unread'),
    path('unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('read-all/', NotificationMarkAllReadView.as_view(), name='notification-read-all'),
    path('<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
]
