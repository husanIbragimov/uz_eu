from rest_framework import serializers

from apps._auth.models import User


class UserMeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    role_key = serializers.CharField(read_only=True)
    side = serializers.CharField(read_only=True, allow_null=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "avatar",
            "role",
            "role_key",
            "role_display",
            "side",
            "date_joined",
        ]
        read_only_fields = ["role"]


class UserShortSerializer(serializers.ModelSerializer):
    """Compact user representation for comments, members and audit entries."""

    full_name = serializers.CharField(read_only=True)
    role_key = serializers.CharField(read_only=True)
    side = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "avatar", "role_key", "side"]
