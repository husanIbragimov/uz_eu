from rest_framework import serializers

from apps.common.utils.phone_validator import international_phone_validator, normalize_phone_number
from apps.projects.models import ProjectContact


class ProjectContactSerializer(serializers.ModelSerializer):
    side_display = serializers.CharField(source="get_side_display", read_only=True)
    # Declared explicitly so `validate_phone` can normalize "+998 90 123 45 67" before the format check.
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)

    class Meta:
        model = ProjectContact
        fields = ("id", "side", "side_display", "full_name", "organization", "position", "email", "phone")
        read_only_fields: tuple[str, ...] = ("id",)

    def validate_phone(self, value: str) -> str:
        value = normalize_phone_number(value)
        if value:
            international_phone_validator(value)
        return value


class NestedProjectContactSerializer(ProjectContactSerializer):
    """Contact row inside the passport save: `id` present -> update, absent -> create."""

    id = serializers.IntegerField(required=False)

    class Meta(ProjectContactSerializer.Meta):
        read_only_fields = ()
