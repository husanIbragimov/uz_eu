from django.core.management.base import BaseCommand

from apps.projects.services.deadline_notifications import notify_approaching_deadlines


class Command(BaseCommand):
    help = "Create in-app notifications for subtasks whose deadline is approaching (cron alternative to Celery beat)."

    def handle(self, *args, **options):
        sent = notify_approaching_deadlines()
        self.stdout.write(self.style.SUCCESS(f"Deadline notifications processed: {sent}"))
