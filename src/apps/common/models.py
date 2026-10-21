from django.db import models
from django.utils import timezone

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimeStamped):
    created_by = models.ForeignKey(
        "_auth.User", null=True, blank=True, on_delete=models.CASCADE, related_name="%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        "_auth.User", null=True, blank=True, on_delete=models.CASCADE, related_name="%(class)s_updated_by",
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def soft_delete(self):
        return self.update(deleted_at=timezone.now())


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    """Default manager that hides soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(BaseModel):
    """BaseModel + soft delete. Rows are never removed; `deleted_at` marks them as gone."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        update_fields = ["deleted_at", "updated_at"]
        if user is not None:
            self.updated_by = user
            update_fields.append("updated_by")
        self.save(update_fields=update_fields)
