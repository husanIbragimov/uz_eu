from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService
from apps.projects.choices import SubtaskStatus
from apps.projects.models import Subtask
from apps.projects.services.indicators import deadline_indicator


def notify_approaching_deadlines(today=None) -> int:
    """Notify project members once per subtask (and per deadline value) when it enters the yellow zone."""
    today = today or timezone.localdate()
    subtasks = (
        Subtask.objects.filter(
            deadline__gte=today,
            deadline__lte=today + timedelta(days=settings.DEADLINE_RISK_DAYS),
            main_task__deleted_at__isnull=True,
            main_task__project__deleted_at__isnull=True,
        )
        .exclude(status=SubtaskStatus.COMPLETED)
        .select_related("main_task__project")
    )
    sent = 0
    for subtask in subtasks:
        sent += NotificationService.notify_project_members(
            subtask.main_task.project,
            NotificationType.DEADLINE,
            {
                "main_task_id": subtask.main_task_id,
                "subtask_id": subtask.pk,
                "subtask_title": subtask.title,
                "deadline": subtask.deadline.isoformat(),
                "days_left": (subtask.deadline - today).days,
                "deadline_indicator": deadline_indicator(subtask.deadline, subtask.status, today=today),
            },
            dedupe_key=f"deadline:{subtask.pk}:{subtask.deadline.isoformat()}",
        )
    return sent
