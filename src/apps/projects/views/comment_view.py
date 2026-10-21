from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.common.base_api import BaseGenericListCreateAPI, BaseGenericUpdateAPI
from apps.common.pagination import PageNumberPagination
from apps.projects.models import Comment
from apps.projects.permissions import ProjectPrivatePermission
from apps.projects.serializers import CommentSerializer
from apps.projects.services import CommentService
from apps.projects.views.mixins import ProjectScopedMixin


def comment_queryset(queryset):
    return queryset.select_related("author", "project").prefetch_related("attachments")


@extend_schema(
    tags=["Comments"],
    parameters=[OpenApiParameter("main_task", OpenApiTypes.INT, description="Filter: comments of one main task")],
)
class CommentListCreateAPIView(ProjectScopedMixin, mixins.ListModelMixin, BaseGenericListCreateAPI):
    """Project comment thread (column 3). Send multipart with repeated `files` to attach files/images."""

    serializer_class = CommentSerializer
    permission_classes = (ProjectPrivatePermission,)
    pagination_class = PageNumberPagination
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "project": self.get_parent_project()}

    def get_queryset(self):
        queryset = comment_queryset(self.get_parent_project().comments.all())
        main_task = self.request.query_params.get("main_task")
        if main_task and main_task.isdigit():
            queryset = queryset.filter(main_task_id=main_task)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = self.validate_data
        comment = CommentService.create(
            request.user,
            self.get_parent_project(),
            body=data.get("body", "").strip(),
            main_task=data.get("main_task"),
            files=data.get("files", []),
        )
        comment = self.get_queryset().get(pk=comment.pk)
        return Response(self.get_serializer(comment).data, status=status.HTTP_201_CREATED)


class CommentPermission(ProjectPrivatePermission):
    """Team members read; only the author (within the edit window) or an admin edits/deletes."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return super().has_object_permission(request, view, obj)
        return CommentService.can_modify(request.user, obj)


@extend_schema(tags=["Comments"])
class CommentDetailAPIView(mixins.RetrieveModelMixin, BaseGenericUpdateAPI):
    serializer_class = CommentSerializer
    permission_classes = (CommentPermission,)

    def get_queryset(self):
        return comment_queryset(Comment.objects.filter(project__deleted_at__isnull=True))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if "pk" in self.kwargs:
            context["project"] = getattr(self.get_queryset().filter(pk=self.kwargs["pk"]).first(), "project", None)
        return context

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        comment = self.get_object()
        if "body" in self.validate_data:
            CommentService.update(request.user, comment, self.validate_data["body"].strip())
        return Response(self.get_serializer(self.get_queryset().get(pk=comment.pk)).data)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        CommentService.delete(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
