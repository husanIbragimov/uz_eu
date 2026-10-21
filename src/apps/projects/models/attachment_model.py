import os

from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.common.models import SoftDeleteModel
from apps.common.utils.file_path_renamer import PathAndRename

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
KIND_BY_EXTENSION = {
    "pdf": "pdf",
    "doc": "doc",
    "docx": "doc",
    "xls": "xls",
    "xlsx": "xls",
    "dwg": "dwg",
    **{ext: "image" for ext in IMAGE_EXTENSIONS},
}


class Attachment(SoftDeleteModel):
    """File attached to exactly one owner: a subtask or a comment. `created_by` is the uploader."""

    subtask = models.ForeignKey(
        "projects.Subtask", on_delete=models.CASCADE, null=True, blank=True, related_name="attachments"
    )
    comment = models.ForeignKey(
        "projects.Comment", on_delete=models.CASCADE, null=True, blank=True, related_name="attachments"
    )
    file = models.FileField(upload_to=PathAndRename("attachments/"), max_length=255, verbose_name=_(T.file))
    file_name = models.CharField(max_length=255, verbose_name=_(T.file_name))
    mime_type = models.CharField(max_length=127, blank=True, default="", verbose_name=_(T.mime_type))
    size = models.PositiveBigIntegerField(default=0, verbose_name=_(T.size))

    class Meta:
        ordering = ("id",)
        verbose_name = _(T.attachment)
        verbose_name_plural = _(T.attachments)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(subtask__isnull=False, comment__isnull=True)
                    | models.Q(subtask__isnull=True, comment__isnull=False)
                ),
                name="attachment_has_exactly_one_owner",
            )
        ]

    def __str__(self):
        return self.file_name

    @property
    def extension(self) -> str:
        return os.path.splitext(self.file_name)[1].lstrip(".").lower()

    @property
    def kind(self) -> str:
        """Icon hint for the UI: image / pdf / doc / xls / dwg / other."""
        return KIND_BY_EXTENSION.get(self.extension, "other")

    @property
    def is_image(self) -> bool:
        return self.extension in IMAGE_EXTENSIONS

    @property
    def project(self):
        return self.subtask.main_task.project if self.subtask_id else self.comment.project
