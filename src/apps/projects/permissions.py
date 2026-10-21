"""RBAC for projects.

- admin: everything.
- uz_representative / eu_representative: create projects; edit projects they are assigned to (ProjectMember).
- viewer / anonymous: read-only public data; never contacts, comments, members or the audit log.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.projects.models import Attachment, Comment, MainTask, Project, ProjectContact, ProjectMember, Subtask


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_admin)


def is_project_member(user, project: Project) -> bool:
    if not (user and user.is_authenticated):
        return False
    return ProjectMember.objects.filter(project=project, user=user).exists()


def can_create_project(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_admin or user.is_representative))


def can_edit_project(user, project: Project) -> bool:
    return is_admin(user) or is_project_member(user, project)


def can_view_private(user, project: Project) -> bool:
    """Contacts, comments, members and history are visible to the people working on the project."""
    return can_edit_project(user, project)


def get_project(obj) -> Project:
    if isinstance(obj, Project):
        return obj
    if isinstance(obj, (ProjectContact, MainTask, Comment)):
        return obj.project
    if isinstance(obj, Subtask):
        return obj.main_task.project
    if isinstance(obj, Attachment):
        return obj.project
    raise TypeError(f"Cannot resolve project for {type(obj).__name__}")


class ProjectEditPermission(BasePermission):
    """Read for everyone; writes only for admin and project members.

    For nested collection endpoints the view exposes `get_parent_project()` so the check runs
    in `initial()`, before request-body validation.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        parent = getattr(view, "get_parent_project", None)
        if parent is not None:
            return can_edit_project(request.user, parent())
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return can_edit_project(request.user, get_project(obj))


class ProjectPrivatePermission(ProjectEditPermission):
    """Like ProjectEditPermission, but reads are also restricted to admin and project members."""

    def has_permission(self, request, view):
        parent = getattr(view, "get_parent_project", None)
        if request.method in SAFE_METHODS:
            if parent is not None:
                return can_view_private(request.user, parent())
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        project = get_project(obj)
        if request.method in SAFE_METHODS:
            return can_view_private(request.user, project)
        return can_edit_project(request.user, project)


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)
