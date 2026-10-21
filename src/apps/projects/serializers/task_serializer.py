from rest_framework import serializers

from apps._auth.serializers.userme_serializer import UserShortSerializer
from apps.common.utils.formatting import format_deadline, format_timestamp
from apps.projects.choices import DeadlineIndicator, MainTaskStatus, SubtaskStatus
from apps.projects.models import MainTask, Subtask
from apps.projects.serializers.attachment_serializer import AttachmentSerializer
from apps.projects.services.indicators import deadline_indicator, main_task_status


class MainTaskSerializer(serializers.ModelSerializer):
    """Expects the queryset to be annotated with `annotate_main_tasks()`."""

    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    subtask_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = MainTask
        fields = ("id", "project", "title", "position", "status", "status_display", "subtask_count", "updated_at")
        read_only_fields = ("id", "project", "position", "updated_at")

    def _status(self, obj) -> str:
        return main_task_status(
            getattr(obj, "subtask_count", 0), getattr(obj, "completed_count", 0), getattr(obj, "started_count", 0)
        )

    def get_status(self, obj) -> str:
        return self._status(obj)

    def get_status_display(self, obj) -> str:
        return MainTaskStatus(self._status(obj)).label


class SubtaskSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=SubtaskStatus.choices, required=False)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    deadline_display = serializers.SerializerMethodField()
    deadline_indicator = serializers.SerializerMethodField()
    deadline_indicator_display = serializers.SerializerMethodField()
    completed_at_display = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    created_by = UserShortSerializer(read_only=True)

    class Meta:
        model = Subtask
        fields = (
            "id",
            "main_task",
            "title",
            "description",
            "deadline",
            "deadline_display",
            "status",
            "status_display",
            "deadline_indicator",
            "deadline_indicator_display",
            "completed_at",
            "completed_at_display",
            "position",
            "attachments",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "main_task", "completed_at", "position", "created_at", "updated_at")
        extra_kwargs = {"deadline": {"required": True}}

    def _indicator(self, obj) -> str:
        return deadline_indicator(obj.deadline, obj.status, obj.completed_at)

    def get_deadline_display(self, obj) -> str:
        return format_deadline(obj.deadline)

    def get_deadline_indicator(self, obj) -> str:
        return self._indicator(obj)

    def get_deadline_indicator_display(self, obj) -> str:
        return DeadlineIndicator(self._indicator(obj)).label

    def get_completed_at_display(self, obj) -> str:
        return format_timestamp(obj.completed_at)


class ReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate ids.")
        return value
