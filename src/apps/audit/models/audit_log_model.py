from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _


class AuditAction(models.TextChoices):
    CREATE = "create", _(T.action_create)
    UPDATE = "update", _(T.action_update)
    DELETE = "delete", _(T.action_delete)


class AuditLog(models.Model):
    """Append-only change history: who changed which field of which entity, and from what to what."""

    user = models.ForeignKey(
        "_auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_(T.user),
    )
    entity = models.CharField(max_length=64, db_index=True, verbose_name=_(T.entity))
    entity_id = models.BigIntegerField(db_index=True, verbose_name=_(T.entity_id))
    # Denormalized so a project's full history (tasks, comments, contacts, ...) is one indexed query.
    project_id = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name=_(T.project))
    action = models.CharField(max_length=16, choices=AuditAction.choices, verbose_name=_(T.action))
    field = models.CharField(max_length=64, blank=True, default="", verbose_name=_(T.field))
    old_value = models.TextField(null=True, blank=True, verbose_name=_(T.old_value))
    new_value = models.TextField(null=True, blank=True, verbose_name=_(T.new_value))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = _(T.audit_log)
        verbose_name_plural = _(T.audit_logs)
        indexes = [models.Index(fields=["entity", "entity_id"])]

    def __str__(self):
        return f"{self.action} {self.entity}#{self.entity_id} {self.field}".strip()
