from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.common.base_api import BaseGenericAPI
from apps.projects.models import Attachment
from apps.projects.permissions import ProjectEditPermission, ProjectPrivatePermission
from apps.projects.serializers import AttachmentSerializer, AttachmentUploadSerializer
from apps.projects.services import AttachmentService, CommentService
from apps.projects.views.mixins import SubtaskScopedMixin


@extend_schema(tags=["Attachments"], responses=AttachmentSerializer)
class SubtaskAttachmentCreateAPIView(SubtaskScopedMixin, BaseGenericAPI):
    """Upload one file (pdf, doc/docx, xls/xlsx, jpg/png, dwg) to a subtask."""

    serializer_class = AttachmentUploadSerializer
    permission_classes = (ProjectEditPermission,)
    parser_classes = (MultiPartParser, FormParser)
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        subtask = self.get_parent_subtask()
        attachment = AttachmentService.create(
            request.user, self.validate_data["file"], project_id=subtask.main_task.project_id, subtask=subtask
        )
        return Response(
            AttachmentSerializer(attachment, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Attachments"])
class AttachmentDetailAPIView(GenericAPIView):
    """GET metadata (+ url for preview/download) or DELETE an attachment.

    Subtask files: readable by everyone, deletable by project editors.
    Comment files: follow comment visibility and the comment edit window.
    """

    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    queryset = Attachment.objects.select_related("subtask__main_task__project", "comment__project")

    def get_object(self):
        attachment = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        if attachment.project.is_deleted:
            raise Http404
        permission = ProjectPrivatePermission() if attachment.comment_id else ProjectEditPermission()
        if not permission.has_object_permission(self.request, self, attachment):
            self.permission_denied(self.request)
        return attachment

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def delete(self, request, *args, **kwargs):
        attachment = self.get_object()
        if attachment.comment_id and not CommentService.can_modify(request.user, attachment.comment):
            raise PermissionDenied("The comment can no longer be edited.")
        AttachmentService.delete(request.user, attachment)
        return Response(status=status.HTTP_204_NO_CONTENT)
