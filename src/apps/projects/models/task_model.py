from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.common.models import SoftDeleteModel
from apps.projects.choices import SubtaskStatus


class MainTask(SoftDeleteModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="main_tasks")
    title = models.CharField(max_length=255, verbose_name=_(T.title))
    position = models.PositiveIntegerField(default=0, verbose_name=_(T.sort_order))
    legacy_pmi_id = models.CharField(max_length=64, unique=True, null=True, blank=True, verbose_name=_(T.legacy_pmi_id))

    class Meta:
        ordering = ("position", "id")
        verbose_name = _(T.main_task)
        verbose_name_plural = _(T.main_tasks)

    def __str__(self):
        return self.title


class Subtask(SoftDeleteModel):
    """Implementation stage of a main task."""

    main_task = models.ForeignKey(MainTask, on_delete=models.CASCADE, related_name="subtasks")
    title = models.CharField(max_length=255, verbose_name=_(T.title))
    description = models.TextField(blank=True, default="", verbose_name=_(T.description))
    deadline = models.DateField(verbose_name=_(T.deadline))
    status = models.CharField(
        max_length=16,
        choices=SubtaskStatus.choices,
        default=SubtaskStatus.NOT_STARTED,
        db_index=True,
        verbose_name=_(T.status),
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_(T.completed_at))
    position = models.PositiveIntegerField(default=0, verbose_name=_(T.sort_order))
    legacy_pmi_id = models.CharField(max_length=64, unique=True, null=True, blank=True, verbose_name=_(T.legacy_pmi_id))

    class Meta:
        ordering = ("position", "id")
        verbose_name = _(T.subtask)
        verbose_name_plural = _(T.subtasks)

    def __str__(self):
        return self.title

    @property
    def project(self):
        return self.main_task.project
