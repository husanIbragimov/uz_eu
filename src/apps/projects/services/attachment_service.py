import mimetypes
import os

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.audit.services import AuditService
from apps.projects.models import Attachment

ATTACHMENT_AUDIT_FIELDS = ("file_name", "mime_type", "size", "subtask", "comment")


def validate_upload(file) -> None:
    """Allowed types: pdf, doc/docx, xls/xlsx, jpg/png, dwg; size limited by ATTACHMENT_MAX_SIZE_MB."""
    extension = os.path.splitext(file.name)[1].lstrip(".").lower()
    allowed = [ext.lower() for ext in settings.ATTACHMENT_ALLOWED_EXTENSIONS]
    if extension not in allowed:
        raise ValidationError(f"File type '.{extension}' is not allowed. Allowed: {', '.join(allowed)}.")
    max_bytes = settings.ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"File '{file.name}' exceeds the {settings.ATTACHMENT_MAX_SIZE_MB} MB limit.")


class AttachmentService:
    @staticmethod
    def create(user, file, project_id: int, subtask=None, comment=None) -> Attachment:
        attachment = Attachment.objects.create(
            subtask=subtask,
            comment=comment,
            file=file,
            file_name=os.path.basename(file.name)[:255],
            mime_type=getattr(file, "content_type", None) or mimetypes.guess_type(file.name)[0] or "",
            size=file.size,
            created_by=user,
            updated_by=user,
        )
        AuditService.log_create(user, attachment, ATTACHMENT_AUDIT_FIELDS, project_id=project_id)
        return attachment

    @staticmethod
    def delete(user, attachment: Attachment) -> None:
        project_id = attachment.project.pk
        attachment.soft_delete(user)
        AuditService.log_delete(user, attachment, project_id=project_id, label=attachment.file_name)
