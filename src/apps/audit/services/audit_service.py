import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from django.db import models
from django.db.models.fields.files import FieldFile

from apps.audit.models import AuditAction, AuditLog


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value), ensure_ascii=False)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, models.Model):
        return str(value.pk)
    return str(value)


class AuditService:
    """Writes field-level create/update/delete entries to AuditLog.

    Usage for updates: take a `snapshot()` before mutating, then call `log_update()` after saving;
    only fields whose serialized value actually changed are written.
    """

    @staticmethod
    def snapshot(instance: models.Model, fields: Iterable[str]) -> dict[str, str | None]:
        data: dict[str, str | None] = {}
        for name in fields:
            field = instance._meta.get_field(name)
            if field.many_to_many:
                values = sorted(str(obj) for obj in getattr(instance, name).all()) if instance.pk else []
                data[name] = _to_text(values)
            elif field.is_relation:
                data[name] = _to_text(getattr(instance, field.attname))
            else:
                data[name] = _to_text(getattr(instance, name))
        return data

    @staticmethod
    def _entity(instance: models.Model) -> str:
        return instance._meta.model_name

    @classmethod
    def log_create(cls, user, instance: models.Model, fields: Iterable[str], project_id=None) -> None:
        values = cls.snapshot(instance, fields)
        AuditLog.objects.bulk_create(
            [
                AuditLog(
                    user=user,
                    entity=cls._entity(instance),
                    entity_id=instance.pk,
                    project_id=project_id,
                    action=AuditAction.CREATE,
                    field=name,
                    new_value=value,
                )
                for name, value in values.items()
                if value not in (None, "", "[]")
            ]
            or [
                AuditLog(
                    user=user,
                    entity=cls._entity(instance),
                    entity_id=instance.pk,
                    project_id=project_id,
                    action=AuditAction.CREATE,
                )
            ]
        )

    @classmethod
    def log_update(cls, user, instance: models.Model, before: dict[str, str | None], project_id=None) -> list[str]:
        after = cls.snapshot(instance, before.keys())
        changed = [name for name in before if before[name] != after[name]]
        AuditLog.objects.bulk_create(
            [
                AuditLog(
                    user=user,
                    entity=cls._entity(instance),
                    entity_id=instance.pk,
                    project_id=project_id,
                    action=AuditAction.UPDATE,
                    field=name,
                    old_value=before[name],
                    new_value=after[name],
                )
                for name in changed
            ]
        )
        return changed

    @classmethod
    def log_delete(cls, user, instance: models.Model, project_id=None, label: str | None = None) -> None:
        AuditLog.objects.create(
            user=user,
            entity=cls._entity(instance),
            entity_id=instance.pk,
            project_id=project_id,
            action=AuditAction.DELETE,
            old_value=label if label is not None else str(instance),
        )

    @classmethod
    def log_field(cls, user, instance: models.Model, field: str, old, new, project_id=None) -> None:
        AuditLog.objects.create(
            user=user,
            entity=cls._entity(instance),
            entity_id=instance.pk,
            project_id=project_id,
            action=AuditAction.UPDATE,
            field=field,
            old_value=_to_text(old),
            new_value=_to_text(new),
        )
