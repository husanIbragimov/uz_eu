from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.common.pagination import PageNumberPagination
from apps.projects.permissions import IsPlatformAdmin

FILTERS = ("entity", "entity_id", "project_id", "user_id", "action")


@extend_schema(tags=["Audit"], parameters=[OpenApiParameter(name, OpenApiTypes.STR) for name in FILTERS])
class AuditLogListAPIView(ListAPIView):
    """Platform-wide audit log (admin only)."""

    serializer_class = AuditLogSerializer
    permission_classes = (IsPlatformAdmin,)
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("user")
        for name in FILTERS:
            value = self.request.query_params.get(name)
            if value:
                queryset = queryset.filter(**{name: value})
        return queryset
