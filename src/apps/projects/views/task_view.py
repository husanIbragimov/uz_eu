from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.base_api import BaseGenericAPI, BaseGenericListCreateAPI, BaseGenericUpdateAPI
from apps.projects.models import Attachment, MainTask, Subtask
from apps.projects.permissions import ProjectEditPermission
from apps.projects.serializers import MainTaskSerializer, ReorderSerializer, SubtaskSerializer
from apps.projects.services import TaskService, annotate_main_tasks
from apps.projects.views.mixins import MainTaskScopedMixin, ProjectScopedMixin


def subtask_queryset(queryset):
    return queryset.select_related("created_by").prefetch_related(
        Prefetch("attachments", queryset=Attachment.objects.all())
    )


def validate_reorder(ids: list[int], queryset) -> None:
    current = set(queryset.values_list("pk", flat=True))
    if set(ids) != current:
        raise ValidationError({"ids": ["Send every item id exactly once, in the new order."]})


# --- main tasks (column 1) ------------------------------------------------------------------------


@extend_schema(tags=["Tasks"])
class MainTaskListCreateAPIView(ProjectScopedMixin, mixins.ListModelMixin, BaseGenericListCreateAPI):
    serializer_class = MainTaskSerializer
    permission_classes = (ProjectEditPermission,)
    pagination_class = None

    def get_queryset(self):
        return annotate_main_tasks(self.get_parent_project().main_tasks.all())

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        task = TaskService.create_main_task(request.user, self.get_parent_project(), dict(self.validate_data))
        task = self.get_queryset().get(pk=task.pk)
        return Response(MainTaskSerializer(task).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Tasks"])
class MainTaskDetailAPIView(mixins.RetrieveModelMixin, BaseGenericUpdateAPI):
    """Rename (PATCH) or delete a main task."""

    serializer_class = MainTaskSerializer
    permission_classes = (ProjectEditPermission,)

    def get_queryset(self):
        return annotate_main_tasks(MainTask.objects.filter(project__deleted_at__isnull=True).select_related("project"))

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        task = TaskService.update_main_task(request.user, self.get_object(), dict(self.validate_data))
        return Response(MainTaskSerializer(self.get_queryset().get(pk=task.pk)).data)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        TaskService.delete_main_task(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Tasks"], responses=MainTaskSerializer(many=True))
class MainTaskReorderAPIView(ProjectScopedMixin, BaseGenericAPI):
    """Drag & drop: send all main task ids of the project in their new order."""

    serializer_class = ReorderSerializer
    permission_classes = (ProjectEditPermission,)
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        project = self.get_parent_project()
        ids = self.validate_data["ids"]
        validate_reorder(ids, project.main_tasks.all())
        TaskService.reorder_main_tasks(request.user, project, ids)
        tasks = annotate_main_tasks(project.main_tasks.all())
        return Response(MainTaskSerializer(tasks, many=True).data)


# --- subtasks (column 2) --------------------------------------------------------------------------


@extend_schema(tags=["Tasks"])
class SubtaskListCreateAPIView(MainTaskScopedMixin, mixins.ListModelMixin, BaseGenericListCreateAPI):
    serializer_class = SubtaskSerializer
    permission_classes = (ProjectEditPermission,)
    pagination_class = None

    def get_queryset(self):
        return subtask_queryset(self.get_parent_main_task().subtasks.all())

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        subtask = TaskService.create_subtask(request.user, self.get_parent_main_task(), self.validate_data)
        subtask = self.get_queryset().get(pk=subtask.pk)
        return Response(SubtaskSerializer(subtask).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Tasks"])
class SubtaskDetailAPIView(mixins.RetrieveModelMixin, BaseGenericUpdateAPI):
    """Edit / change status / delete a subtask (card "⋮" menu)."""

    serializer_class = SubtaskSerializer
    permission_classes = (ProjectEditPermission,)

    def get_queryset(self):
        return subtask_queryset(
            Subtask.objects.filter(
                main_task__deleted_at__isnull=True, main_task__project__deleted_at__isnull=True
            ).select_related("main_task__project")
        )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        subtask = TaskService.update_subtask(request.user, self.get_object(), self.validate_data)
        return Response(SubtaskSerializer(self.get_queryset().get(pk=subtask.pk)).data)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        TaskService.delete_subtask(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Tasks"], responses=SubtaskSerializer(many=True))
class SubtaskReorderAPIView(MainTaskScopedMixin, BaseGenericAPI):
    serializer_class = ReorderSerializer
    permission_classes = (ProjectEditPermission,)
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        main_task = self.get_parent_main_task()
        ids = self.validate_data["ids"]
        validate_reorder(ids, main_task.subtasks.all())
        TaskService.reorder_subtasks(request.user, main_task, ids)
        return Response(SubtaskSerializer(subtask_queryset(main_task.subtasks.all()), many=True).data)
