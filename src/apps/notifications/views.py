from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import PageNumberPagination
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


@extend_schema(
    tags=["Notifications"],
    parameters=[OpenApiParameter("unread", OpenApiTypes.BOOL, description="Only unread notifications")],
)
class NotificationListAPIView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") in ("1", "true", "True"):
            queryset = queryset.filter(read_at__isnull=True)
        return queryset


@extend_schema(
    tags=["Notifications"], responses=inline_serializer("UnreadCount", {"count": serializers.IntegerField()})
)
class NotificationUnreadCountAPIView(APIView):
    """Bell counter."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        count = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
        return Response({"count": count})


@extend_schema(tags=["Notifications"], request=None, responses=NotificationSerializer)
class NotificationReadAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


@extend_schema(
    tags=["Notifications"],
    request=None,
    responses=inline_serializer("ReadAll", {"updated": serializers.IntegerField()}),
)
class NotificationReadAllAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated}, status=status.HTTP_200_OK)
