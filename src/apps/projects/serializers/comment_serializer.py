from rest_framework import serializers

from apps._auth.serializers.userme_serializer import UserShortSerializer
from apps.common.choices import SideChoice
from apps.common.utils.formatting import format_timestamp
from apps.projects.models import Comment, MainTask
from apps.projects.serializers.attachment_serializer import AttachmentSerializer
from apps.projects.services.attachment_service import validate_upload
from apps.projects.services.comment_service import CommentService


class CommentSerializer(serializers.ModelSerializer):
    main_task = serializers.PrimaryKeyRelatedField(queryset=MainTask.objects.all(), required=False, allow_null=True)
    author = UserShortSerializer(read_only=True)
    side = serializers.SerializerMethodField()
    side_display = serializers.SerializerMethodField()
    body = serializers.CharField(required=False, allow_blank=True)
    files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    attachments = AttachmentSerializer(many=True, read_only=True)
    is_edited = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id",
            "project",
            "main_task",
            "author",
            "side",
            "side_display",
            "body",
            "files",
            "attachments",
            "is_edited",
            "edited_at",
            "can_edit",
            "created_at",
            "created_at_display",
        )
        read_only_fields = ("id", "project", "edited_at", "created_at")

    def validate_main_task(self, value):
        project = self.context.get("project")
        if value is not None and project is not None and value.project_id != project.pk:
            raise serializers.ValidationError("Main task does not belong to this project.")
        return value

    def validate_files(self, value):
        for file in value:
            validate_upload(file)
        return value

    def validate(self, attrs):
        if self.instance is None and not (attrs.get("body", "").strip() or attrs.get("files")):
            raise serializers.ValidationError({"body": ["Write a comment or attach a file."]})
        if self.instance is not None and not attrs.get("body", self.instance.body).strip():
            raise serializers.ValidationError({"body": ["Comment text cannot be empty."]})
        return attrs

    def get_side(self, obj) -> str | None:
        return obj.author.side

    def get_side_display(self, obj) -> str | None:
        side = obj.author.side
        return SideChoice(side).label if side else None

    def get_is_edited(self, obj) -> bool:
        return obj.edited_at is not None

    def get_can_edit(self, obj) -> bool:
        request = self.context.get("request")
        return CommentService.can_modify(getattr(request, "user", None), obj)

    def get_created_at_display(self, obj) -> str:
        return format_timestamp(obj.created_at)
