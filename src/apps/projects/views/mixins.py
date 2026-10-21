from django.shortcuts import get_object_or_404

from apps.projects.models import MainTask, Project, Subtask


class ProjectScopedMixin:
    """For endpoints nested under /projects/<project_pk>/...; used by the permission classes."""

    kwargs: dict

    def get_parent_project(self) -> Project:
        if not hasattr(self, "_parent_project"):
            self._parent_project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return self._parent_project


class MainTaskScopedMixin:
    """For endpoints nested under /main-tasks/<main_task_pk>/..."""

    kwargs: dict

    def get_parent_main_task(self) -> MainTask:
        if not hasattr(self, "_parent_main_task"):
            self._parent_main_task = get_object_or_404(
                MainTask.objects.select_related("project").filter(project__deleted_at__isnull=True),
                pk=self.kwargs["main_task_pk"],
            )
        return self._parent_main_task

    def get_parent_project(self) -> Project:
        return self.get_parent_main_task().project


class SubtaskScopedMixin:
    """For endpoints nested under /subtasks/<subtask_pk>/..."""

    kwargs: dict

    def get_parent_subtask(self) -> Subtask:
        if not hasattr(self, "_parent_subtask"):
            self._parent_subtask = get_object_or_404(
                Subtask.objects.select_related("main_task__project").filter(
                    main_task__deleted_at__isnull=True, main_task__project__deleted_at__isnull=True
                ),
                pk=self.kwargs["subtask_pk"],
            )
        return self._parent_subtask

    def get_parent_project(self) -> Project:
        return self.get_parent_subtask().main_task.project
