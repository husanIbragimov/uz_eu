from django.db.models import Count, F, Min, Q, Sum
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.common.base_api import BaseGenericAPI, BaseGenericListCreateAPI, BaseGenericUpdateAPI
from apps.common.pagination import PageNumberPagination
from apps.common.utils.formatting import format_money
from apps.projects.choices import ProjectCategory
from apps.projects.models import Project
from apps.projects.permissions import (
    ProjectEditPermission,
    ProjectPrivatePermission,
    can_create_project,
    can_edit_project,
    is_admin,
)
from apps.projects.serializers import (
    PROJECT_SORT_FIELDS,
    CategoryHistorySerializer,
    ProjectCategorySerializer,
    ProjectDetailSerializer,
    ProjectListQuerySerializer,
    ProjectListSerializer,
    ProjectStatsSerializer,
)
from apps.projects.services import ProjectService
from apps.projects.views.mixins import ProjectScopedMixin
from apps.reference.models import Country

LIST_PARAMETERS = [
    OpenApiParameter("category", OpenApiTypes.STR, enum=ProjectCategory.values),
    OpenApiParameter("search", OpenApiTypes.STR, description="Search by project name or ID"),
    OpenApiParameter("sector", OpenApiTypes.INT),
    OpenApiParameter("country", OpenApiTypes.STR, description="Country id or ISO code"),
    OpenApiParameter("initiator", OpenApiTypes.INT),
    OpenApiParameter("status", OpenApiTypes.STR),
    OpenApiParameter("region", OpenApiTypes.INT),
    OpenApiParameter("district", OpenApiTypes.INT),
    OpenApiParameter("sort", OpenApiTypes.STR, enum=list(PROJECT_SORT_FIELDS)),
    OpenApiParameter("order", OpenApiTypes.STR, enum=["asc", "desc"]),
]


def detail_queryset():
    return Project.objects.select_related("sector", "district__parent", "initiator").prefetch_related(
        "countries", "eu_partners", "uz_partners", "contacts"
    )


# query param -> ORM lookup for the simple equality filters of the projects table
EXACT_FILTERS = {
    "category": "category",
    "sector": "sector_id",
    "initiator": "initiator_id",
    "status": "status",
    "region": "district__parent_id",
    "district": "district_id",
}
SORT_ANNOTATIONS = {
    "country": {"country_sort": Min("countries__name")},
    "partner": {"partner_sort": Min("eu_partners__name")},
}


def _country_project_ids(country: str):
    country_filter = {"pk": country} if country.isdigit() else {"iso_code__iexact": country}
    country_ids = Country.objects.filter(**country_filter).values("pk")
    return Project.countries.through.objects.filter(country_id__in=country_ids).values("project_id")


def filter_projects(queryset, params: dict):
    """Filtering + server-side sorting for the projects table."""
    queryset = queryset.select_related("sector", "initiator").prefetch_related("countries", "eu_partners")

    exact = {lookup: params[name] for name, lookup in EXACT_FILTERS.items() if params.get(name)}
    queryset = queryset.filter(**exact)
    if params.get("search"):
        search = params["search"].strip()
        queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))
    if params.get("country"):
        queryset = queryset.filter(pk__in=_country_project_ids(params["country"]))

    sort = params.get("sort", "updated")
    queryset = queryset.annotate(**SORT_ANNOTATIONS.get(sort, {}))
    expression = F(PROJECT_SORT_FIELDS[sort])
    descending = params.get("order", "desc") == "desc"
    ordering = expression.desc(nulls_last=True) if descending else expression.asc(nulls_last=True)
    return queryset.order_by(ordering, "-id" if descending else "id")


class ProjectTableMixin(GenericAPIView):
    """Shared table rendering: validated query params, pagination and the `#` row number."""

    pagination_class = PageNumberPagination

    def list_projects(self, request, queryset):
        query = ProjectListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        queryset = filter_projects(queryset, query.validated_data)

        page = self.paginate_queryset(queryset)
        rows = ProjectListSerializer(page, many=True, context=self.get_serializer_context()).data
        offset = (self.paginator.page.number - 1) * self.paginator.page.paginator.per_page
        for index, row in enumerate(rows, start=1):
            row["row_number"] = offset + index
        return self.get_paginated_response(rows)


class ProjectCreatePermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or can_create_project(request.user)


@extend_schema(tags=["Projects"])
class ProjectListCreateAPIView(ProjectTableMixin, BaseGenericListCreateAPI):
    """GET: projects table (public). POST: create a project (admin / representatives)."""

    serializer_class = ProjectDetailSerializer
    permission_classes = (ProjectCreatePermission,)
    queryset = Project.objects.all()

    @extend_schema(parameters=LIST_PARAMETERS, responses=ProjectListSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return self.list_projects(request, self.get_queryset())

    def post(self, request, *args, **kwargs):
        project = ProjectService.create(request.user, self.validate_data)
        data = ProjectDetailSerializer(detail_queryset().get(pk=project.pk), context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Projects"], parameters=LIST_PARAMETERS, responses=ProjectListSerializer(many=True))
class MyProjectListAPIView(ProjectTableMixin, ListAPIView):
    """Personal account: projects the current user is assigned to."""

    serializer_class = ProjectListSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        queryset = Project.objects.filter(memberships__user=request.user)
        return self.list_projects(request, queryset)


@extend_schema(tags=["Projects"], responses=ProjectStatsSerializer)
class ProjectStatsAPIView(APIView):
    """Header badge + analytics cards: totals per category (potential: count only)."""

    permission_classes = (AllowAny,)

    def get(self, request):
        rows = {
            row["category"]: row
            for row in Project.objects.order_by().values("category").annotate(count=Count("id"), total_cost=Sum("cost"))
        }
        by_category = {}
        for category in ProjectCategory.values:
            row = rows.get(category, {"count": 0, "total_cost": None})
            stats = {"count": row["count"]}
            if category != ProjectCategory.POTENTIAL:
                total_cost = row["total_cost"] or 0
                stats["total_cost"] = f"{total_cost:.2f}"
                stats["total_cost_display"] = format_money(total_cost)
            by_category[category] = stats
        total = sum(item["count"] for item in by_category.values())
        return Response({"total": total, "by_category": by_category})


class ProjectDetailPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return is_admin(request.user)
        return can_edit_project(request.user, obj)


@extend_schema(tags=["Projects"])
class ProjectDetailAPIView(mixins.RetrieveModelMixin, BaseGenericUpdateAPI):
    """Project Passport. PUT/PATCH saves General Information and, if `contacts` is sent, the contact list."""

    serializer_class = ProjectDetailSerializer
    permission_classes = (ProjectDetailPermission,)

    def get_queryset(self):
        return detail_queryset()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        project = ProjectService.update(request.user, self.get_object(), self.validate_data)
        data = ProjectDetailSerializer(detail_queryset().get(pk=project.pk), context=self.get_serializer_context()).data
        return Response(data)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        ProjectService.delete(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Projects"], responses=ProjectDetailSerializer)
class ProjectCategoryAPIView(ProjectScopedMixin, BaseGenericAPI):
    """Move the project to another category; tasks, comments and files are kept."""

    serializer_class = ProjectCategorySerializer
    permission_classes = (ProjectEditPermission,)
    # perform_check validates the body on every method, so expose PATCH only
    http_method_names = ["patch"]

    def patch(self, request, *args, **kwargs):
        project = self.get_parent_project()
        ProjectService.change_category(request.user, project, self.validate_data["category"])
        data = ProjectDetailSerializer(detail_queryset().get(pk=project.pk), context=self.get_serializer_context()).data
        return Response(data)


@extend_schema(tags=["Projects"])
class CategoryHistoryListAPIView(ProjectScopedMixin, ListAPIView):
    serializer_class = CategoryHistorySerializer
    permission_classes = (ProjectPrivatePermission,)
    pagination_class = None

    def get_queryset(self):
        return self.get_parent_project().category_history.select_related("changed_by")


@extend_schema(
    tags=["Projects"],
    parameters=[OpenApiParameter("entity", OpenApiTypes.STR), OpenApiParameter("entity_id", OpenApiTypes.INT)],
)
class ProjectAuditLogAPIView(ProjectScopedMixin, ListAPIView):
    """Full change history of a project and everything inside it."""

    serializer_class = AuditLogSerializer
    permission_classes = (ProjectPrivatePermission,)
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = AuditLog.objects.filter(project_id=self.get_parent_project().pk).select_related("user")
        entity = self.request.query_params.get("entity")
        entity_id = self.request.query_params.get("entity_id")
        if entity:
            queryset = queryset.filter(entity=entity)
        if entity_id and entity_id.isdigit():
            queryset = queryset.filter(entity_id=entity_id)
        return queryset
