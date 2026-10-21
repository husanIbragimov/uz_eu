from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import MainTask, Project, Subtask

SEARCH_LIMIT = 10


@extend_schema(tags=["Search"], parameters=[OpenApiParameter("q", OpenApiTypes.STR, required=True)])
class GlobalSearchAPIView(APIView):
    """Header search "Search projects, tasks…"."""

    permission_classes = (AllowAny,)

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            raise ValidationError({"q": ["Enter at least 2 characters."]})

        projects = (Project.objects.filter(name__icontains=query) | Project.objects.filter(code__icontains=query))[
            :SEARCH_LIMIT
        ]
        main_tasks = MainTask.objects.filter(title__icontains=query, project__deleted_at__isnull=True).select_related(
            "project"
        )[:SEARCH_LIMIT]
        subtasks = Subtask.objects.filter(
            title__icontains=query,
            main_task__deleted_at__isnull=True,
            main_task__project__deleted_at__isnull=True,
        ).select_related("main_task__project")[:SEARCH_LIMIT]

        return Response(
            {
                "projects": [
                    {"id": p.pk, "project_id": p.code, "name": p.name, "category": p.category} for p in projects
                ],
                "main_tasks": [
                    {"id": t.pk, "title": t.title, "project": {"id": t.project_id, "name": t.project.name}}
                    for t in main_tasks
                ],
                "subtasks": [
                    {
                        "id": s.pk,
                        "title": s.title,
                        "main_task_id": s.main_task_id,
                        "project": {"id": s.main_task.project_id, "name": s.main_task.project.name},
                    }
                    for s in subtasks
                ],
            }
        )
