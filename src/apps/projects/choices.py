from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _


class ProjectCategory(models.TextChoices):
    ONGOING = "ongoing", _(T.category_ongoing)
    UPCOMING = "upcoming", _(T.category_upcoming)
    POTENTIAL = "potential", _(T.category_potential)


class ProjectStatus(models.TextChoices):
    NOT_STARTED = "not_started", _(T.project_status_not_started)
    IN_PROGRESS = "in_progress", _(T.project_status_in_progress)
    ON_HOLD = "on_hold", _(T.project_status_on_hold)
    COMPLETED = "completed", _(T.project_status_completed)


class SubtaskStatus(models.TextChoices):
    NOT_STARTED = "not_started", _(T.subtask_status_not_started)
    IN_PROGRESS = "in_progress", _(T.subtask_status_in_progress)
    UNDER_REVIEW = "under_review", _(T.subtask_status_under_review)
    COMPLETED = "completed", _(T.subtask_status_completed)


class MainTaskStatus(models.TextChoices):
    """Derived from subtasks, never stored."""

    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class DeadlineIndicator(models.TextChoices):
    """Computed from deadline + workflow status, never stored."""

    GREEN = "green", "On time"
    YELLOW = "yellow", "Risk of delay"
    RED = "red", "Overdue"
