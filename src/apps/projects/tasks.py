from celery import shared_task

from apps.projects.services.deadline_notifications import notify_approaching_deadlines


@shared_task(name="apps.projects.tasks.notify_approaching_deadlines")
def notify_approaching_deadlines_task() -> int:
    return notify_approaching_deadlines()
