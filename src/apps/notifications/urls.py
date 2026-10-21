from django.urls import path

from apps.notifications.views import (
    NotificationListAPIView,
    NotificationReadAllAPIView,
    NotificationReadAPIView,
    NotificationUnreadCountAPIView,
)

urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="list"),
    path("unread-count/", NotificationUnreadCountAPIView.as_view(), name="unread-count"),
    path("read-all/", NotificationReadAllAPIView.as_view(), name="read-all"),
    path("<int:pk>/read/", NotificationReadAPIView.as_view(), name="read"),
]
