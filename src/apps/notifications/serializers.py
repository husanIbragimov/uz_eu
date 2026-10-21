from rest_framework import serializers

from apps.common.utils.formatting import format_timestamp
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    is_read = serializers.SerializerMethodField()
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ("id", "type", "type_display", "payload", "is_read", "read_at", "created_at", "created_at_display")

    def get_is_read(self, obj) -> bool:
        return obj.read_at is not None

    def get_created_at_display(self, obj) -> str:
        return format_timestamp(obj.created_at)
