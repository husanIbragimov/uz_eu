from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService
from apps.projects.models import Comment, Project
from apps.projects.permissions import is_admin
from apps.projects.services.attachment_service import AttachmentService

COMMENT_AUDIT_FIELDS = ("body", "main_task")


class CommentService:
    @staticmethod
    def can_modify(user, comment: Comment, now=None) -> bool:
        """Admin always; the author only within COMMENT_EDIT_WINDOW_MINUTES of posting."""
        if is_admin(user):
            return True
        if not (user and user.is_authenticated and comment.author_id == user.pk):
            return False
        now = now or timezone.now()
        return now - comment.created_at <= timedelta(minutes=settings.COMMENT_EDIT_WINDOW_MINUTES)

    @staticmethod
    @transaction.atomic
    def create(user, project: Project, body: str, main_task=None, files=()) -> Comment:
        comment = Comment.objects.create(
            project=project, main_task=main_task, author=user, body=body, created_by=user, updated_by=user
        )
        AuditService.log_create(user, comment, COMMENT_AUDIT_FIELDS, project_id=project.pk)
        for file in files:
            AttachmentService.create(user, file, project_id=project.pk, comment=comment)

        NotificationService.notify_project_members(
            project,
            NotificationType.COMMENT,
            {
                "comment_id": comment.pk,
                "main_task_id": comment.main_task_id,
                "author": user.full_name,
                "preview": body[:140],
            },
            actor=user,
        )
        return comment

    @staticmethod
    @transaction.atomic
    def update(user, comment: Comment, body: str) -> Comment:
        """Previous text is preserved in the audit log; the comment is labelled as edited."""
        before = AuditService.snapshot(comment, COMMENT_AUDIT_FIELDS)
        comment.body = body
        comment.edited_at = timezone.now()
        comment.updated_by = user
        comment.save(update_fields=["body", "edited_at", "updated_by", "updated_at"])
        AuditService.log_update(user, comment, before, project_id=comment.project_id)
        return comment

    @staticmethod
    @transaction.atomic
    def delete(user, comment: Comment) -> None:
        comment.soft_delete(user)
        AuditService.log_delete(user, comment, project_id=comment.project_id, label=comment.body)
