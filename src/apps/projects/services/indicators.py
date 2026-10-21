"""Pure business rules for task status and deadline indicators (unit-tested at boundary dates)."""

from datetime import date, datetime

from django.conf import settings
from django.utils import timezone

from apps.projects.choices import DeadlineIndicator, MainTaskStatus, SubtaskStatus


def deadline_indicator(
    deadline: date,
    status: str,
    completed_at: datetime | None = None,
    today: date | None = None,
    risk_days: int | None = None,
) -> str:
    """
    green  - completed on/before the deadline, or not completed with more than N days left;
    yellow - not completed and 0..N days left (risk of delay);
    red    - not completed and the deadline has passed, or completed after the deadline.
    """
    today = today or timezone.localdate()
    risk_days = settings.DEADLINE_RISK_DAYS if risk_days is None else risk_days

    if status == SubtaskStatus.COMPLETED:
        if completed_at is None:
            completed_on = today
        elif isinstance(completed_at, datetime):
            completed_on = timezone.localdate(completed_at) if timezone.is_aware(completed_at) else completed_at.date()
        else:
            completed_on = completed_at
        return DeadlineIndicator.GREEN if completed_on <= deadline else DeadlineIndicator.RED

    days_left = (deadline - today).days
    if days_left < 0:
        return DeadlineIndicator.RED
    if days_left <= risk_days:
        return DeadlineIndicator.YELLOW
    return DeadlineIndicator.GREEN


def main_task_status(total: int, completed: int, started: int) -> str:
    """all subtasks completed -> completed; any started (status != not_started) -> in progress; else pending."""
    if total and completed == total:
        return MainTaskStatus.COMPLETED
    if started:
        return MainTaskStatus.IN_PROGRESS
    return MainTaskStatus.PENDING
