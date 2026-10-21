from rest_framework import serializers

from apps.common.utils.formatting import format_timestamp
from apps.projects.models import Attachment
from apps.projects.services.attachment_service import validate_upload


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.FileField(source="file", read_only=True)
    kind = serializers.CharField(read_only=True)
    is_image = serializers.BooleanField(read_only=True)
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = (
            "id",
            "file_name",
            "url",
            "mime_type",
            "size",
            "kind",
            "is_image",
            "created_by",
            "created_at",
            "created_at_display",
        )
        read_only_fields = fields

    def get_created_at_display(self, obj) -> str:
        return format_timestamp(obj.created_at)


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        validate_upload(value)
        return value
