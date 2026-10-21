from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.response import Response

from apps.common.base_api import BaseGenericListCreateAPI, BaseGenericUpdateAPI
from apps.projects.permissions import ProjectPrivatePermission
from apps.projects.serializers import ProjectContactSerializer
from apps.projects.services import ProjectService
from apps.projects.views.mixins import ProjectScopedMixin


@extend_schema(tags=["Project contacts"])
class ProjectContactListCreateAPIView(ProjectScopedMixin, mixins.ListModelMixin, BaseGenericListCreateAPI):
    """Block 2 of the passport. Hidden from viewers; "+ Add Partner" posts here."""

    serializer_class = ProjectContactSerializer
    permission_classes = (ProjectPrivatePermission,)
    pagination_class = None

    def get_queryset(self):
        return self.get_parent_project().contacts.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        contact = ProjectService.create_contact(request.user, self.get_parent_project(), dict(self.validate_data))
        return Response(ProjectContactSerializer(contact).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Project contacts"])
class ProjectContactDetailAPIView(ProjectScopedMixin, mixins.RetrieveModelMixin, BaseGenericUpdateAPI):
    serializer_class = ProjectContactSerializer
    permission_classes = (ProjectPrivatePermission,)

    def get_queryset(self):
        return self.get_parent_project().contacts.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        contact = ProjectService.update_contact(request.user, self.get_object(), dict(self.validate_data))
        return Response(ProjectContactSerializer(contact).data)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        ProjectService.delete_contact(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
