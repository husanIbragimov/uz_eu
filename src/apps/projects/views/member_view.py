from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps._auth.models import User
from apps.common.base_api import BaseGenericListCreateAPI
from apps.projects.permissions import IsPlatformAdmin, ProjectPrivatePermission, is_admin
from apps.projects.serializers import ProjectMemberSerializer
from apps.projects.services import ProjectService
from apps.projects.views.mixins import ProjectScopedMixin


class MemberPermission(ProjectPrivatePermission):
    """Members are visible to the project team; only admins assign or remove them."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return super().has_permission(request, view)
        return is_admin(request.user)


@extend_schema(tags=["Project members"])
class ProjectMemberListCreateAPIView(ProjectScopedMixin, mixins.ListModelMixin, BaseGenericListCreateAPI):
    serializer_class = ProjectMemberSerializer
    permission_classes = (MemberPermission,)
    pagination_class = None

    def get_queryset(self):
        return self.get_parent_project().memberships.select_related("user")

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = User.objects.get(pk=self.validate_data["user_id"])
        membership = ProjectService.add_member(request.user, self.get_parent_project(), user)
        return Response(ProjectMemberSerializer(membership).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Project members"])
class ProjectMemberDeleteAPIView(ProjectScopedMixin, APIView):
    permission_classes = (IsPlatformAdmin,)

    def delete(self, request, project_pk, user_id):
        membership = get_object_or_404(self.get_parent_project().memberships, user_id=user_id)
        ProjectService.remove_member(request.user, membership)
        return Response(status=status.HTTP_204_NO_CONTENT)
