from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.common.models import SoftDeleteModel


class Comment(SoftDeleteModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="comments")
    main_task = models.ForeignKey(
        "projects.MainTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
        verbose_name=_(T.main_task),
    )
    author = models.ForeignKey("_auth.User", on_delete=models.PROTECT, related_name="comments")
    body = models.TextField(blank=True, default="", verbose_name=_(T.body))
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name=_(T.edited_at))

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = _(T.comment)
        verbose_name_plural = _(T.comments)

    def __str__(self):
        return f"{self.author}: {self.body[:40]}"
