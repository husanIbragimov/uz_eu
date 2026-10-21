from django.db import transaction
from django.db.models import Count, Max, Q, QuerySet
from django.utils import timezone

from apps.audit.services import AuditService
from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService
from apps.projects.choices import SubtaskStatus
from apps.projects.models import MainTask, Project, Subtask
from apps.projects.services.project_service import MAIN_TASK_AUDIT_FIELDS

SUBTASK_AUDIT_FIELDS = ("title", "description", "deadline", "status", "completed_at", "position")
STARTED_STATUSES = (SubtaskStatus.IN_PROGRESS, SubtaskStatus.UNDER_REVIEW, SubtaskStatus.COMPLETED)


def annotate_main_tasks(queryset: QuerySet) -> QuerySet:
    """Adds subtask_count / completed_count / started_count used to derive the main task status."""
    alive = Q(subtasks__deleted_at__isnull=True)
    # Meta.ordering is ignored for GROUP BY queries, so the column order must be explicit.
    return queryset.annotate(
        subtask_count=Count("subtasks", filter=alive),
        completed_count=Count("subtasks", filter=alive & Q(subtasks__status=SubtaskStatus.COMPLETED)),
        started_count=Count("subtasks", filter=alive & Q(subtasks__status__in=STARTED_STATUSES)),
    ).order_by("position", "id")


def _next_position(queryset: QuerySet) -> int:
    return (queryset.aggregate(value=Max("position"))["value"] or 0) + 1


def _apply_status(subtask: Subtask, status: str) -> None:
    subtask.status = status
    if status == SubtaskStatus.COMPLETED:
        subtask.completed_at = subtask.completed_at or timezone.now()
    else:
        subtask.completed_at = None


def _reorder(user, queryset: QuerySet, ordered_ids: list[int], project_id: int) -> None:
    items = {item.pk: item for item in queryset}
    for position, item_id in enumerate(ordered_ids, start=1):
        item = items[item_id]
        if item.position != position:
            AuditService.log_field(user, item, "position", item.position, position, project_id=project_id)
            item.position = position
            item.updated_by = user
            item.save(update_fields=["position", "updated_by", "updated_at"])


class TaskService:
    # --- main tasks -----------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_main_task(user, project: Project, data: dict) -> MainTask:
        data.setdefault("position", _next_position(project.main_tasks.all()))
        task = MainTask.objects.create(project=project, created_by=user, updated_by=user, **data)
        AuditService.log_create(user, task, MAIN_TASK_AUDIT_FIELDS, project_id=project.pk)
        return task

    @staticmethod
    @transaction.atomic
    def update_main_task(user, task: MainTask, data: dict) -> MainTask:
        before = AuditService.snapshot(task, MAIN_TASK_AUDIT_FIELDS)
        for name, value in data.items():
            setattr(task, name, value)
        task.updated_by = user
        task.save()
        AuditService.log_update(user, task, before, project_id=task.project_id)
        return task

    @staticmethod
    @transaction.atomic
    def delete_main_task(user, task: MainTask) -> None:
        for subtask in task.subtasks.all():
            subtask.soft_delete(user)
            AuditService.log_delete(user, subtask, project_id=task.project_id)
        task.soft_delete(user)
        AuditService.log_delete(user, task, project_id=task.project_id)

    @staticmethod
    @transaction.atomic
    def reorder_main_tasks(user, project: Project, ordered_ids: list[int]) -> None:
        _reorder(user, project.main_tasks.all(), ordered_ids, project.pk)

    # --- subtasks -------------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_subtask(user, main_task: MainTask, data: dict) -> Subtask:
        data = dict(data)
        status = data.pop("status", SubtaskStatus.NOT_STARTED)
        data.setdefault("position", _next_position(main_task.subtasks.all()))
        subtask = Subtask(main_task=main_task, created_by=user, updated_by=user, **data)
        _apply_status(subtask, status)
        subtask.save()
        AuditService.log_create(user, subtask, SUBTASK_AUDIT_FIELDS, project_id=main_task.project_id)
        return subtask

    @staticmethod
    @transaction.atomic
    def update_subtask(user, subtask: Subtask, data: dict) -> Subtask:
        data = dict(data)
        project = subtask.main_task.project
        before = AuditService.snapshot(subtask, SUBTASK_AUDIT_FIELDS)
        old_status = subtask.status
        if "status" in data:
            _apply_status(subtask, data.pop("status"))
        for name, value in data.items():
            setattr(subtask, name, value)
        subtask.updated_by = user
        subtask.save()
        AuditService.log_update(user, subtask, before, project_id=project.pk)

        if subtask.status != old_status:
            NotificationService.notify_project_members(
                project,
                NotificationType.STATUS_CHANGE,
                {
                    "main_task_id": subtask.main_task_id,
                    "subtask_id": subtask.pk,
                    "subtask_title": subtask.title,
                    "old_status": old_status,
                    "new_status": subtask.status,
                    "changed_by": user.full_name if user else None,
                },
                actor=user,
            )
        return subtask

    @staticmethod
    @transaction.atomic
    def delete_subtask(user, subtask: Subtask) -> None:
        subtask.soft_delete(user)
        AuditService.log_delete(user, subtask, project_id=subtask.main_task.project_id)

    @staticmethod
    @transaction.atomic
    def reorder_subtasks(user, main_task: MainTask, ordered_ids: list[int]) -> None:
        _reorder(user, main_task.subtasks.all(), ordered_ids, main_task.project_id)
