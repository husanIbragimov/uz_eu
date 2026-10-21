from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _


class NotificationType(models.TextChoices):
    COMMENT = "comment", _(T.notification_comment)
    STATUS_CHANGE = "status_change", _(T.notification_status)
    DEADLINE = "deadline", _(T.notification_deadline)


class Notification(models.Model):
    """In-app notification shown under the bell icon."""

    user = models.ForeignKey("_auth.User", on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=32, choices=NotificationType.choices, verbose_name=_(T.notification_type))
    payload = models.JSONField(default=dict, blank=True, verbose_name=_(T.payload))
    # Lets periodic jobs (approaching deadlines) skip notifications they already sent.
    dedupe_key = models.CharField(max_length=128, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_(T.read_at))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = _(T.notification)
        verbose_name_plural = _(T.notifications)
        indexes = [models.Index(fields=["user", "read_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                condition=~models.Q(dedupe_key=""),
                name="unique_notification_dedupe_key",
            )
        ]

    def __str__(self):
        return f"{self.type} -> {self.user_id}"
