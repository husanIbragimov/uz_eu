from rest_framework import serializers

from apps._auth.serializers.userme_serializer import UserShortSerializer
from apps.audit.models import AuditLog
from apps.common.utils.formatting import format_timestamp


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "entity",
            "entity_id",
            "action",
            "field",
            "old_value",
            "new_value",
            "created_at",
            "created_at_display",
        )
        read_only_fields = fields

    def get_created_at_display(self, obj) -> str:
        return format_timestamp(obj.created_at)
