from typing import Iterable

from apps.notifications.models import Notification


class NotificationService:
    @staticmethod
    def notify(user_ids: Iterable[int], type: str, payload: dict, exclude_user_id=None, dedupe_key: str = "") -> int:
        notifications = [
            Notification(user_id=user_id, type=type, payload=payload, dedupe_key=dedupe_key)
            for user_id in set(user_ids)
            if user_id != exclude_user_id
        ]
        # ignore_conflicts: a dedupe_key that was already delivered to a user is silently skipped
        Notification.objects.bulk_create(notifications, ignore_conflicts=bool(dedupe_key))
        return len(notifications)

    @classmethod
    def notify_project_members(cls, project, type: str, payload: dict, actor=None, dedupe_key: str = "") -> int:
        member_ids = project.memberships.values_list("user_id", flat=True)
        payload = {"project_id": project.pk, "project_code": project.code, "project_name": project.name, **payload}
        return cls.notify(
            member_ids,
            type,
            payload,
            exclude_user_id=getattr(actor, "pk", None),
            dedupe_key=dedupe_key,
        )
