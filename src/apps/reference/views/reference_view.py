from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from apps.reference.models import Country, Organization, Region, Sector
from apps.reference.serializers import CountrySerializer, OrganizationSerializer, RegionSerializer, SectorSerializer


class _ReferenceListAPIView(ListAPIView):
    """Unpaginated read-only lookup lists used to fill selects/autocomplete. Managed in Django admin."""

    permission_classes = (AllowAny,)
    pagination_class = None


@extend_schema(tags=["Reference"])
class SectorListAPIView(_ReferenceListAPIView):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


@extend_schema(
    tags=["Reference"],
    parameters=[OpenApiParameter("search", OpenApiTypes.STR, description="Filter by name (case-insensitive)")],
)
class CountryListAPIView(_ReferenceListAPIView):
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = Country.objects.filter(is_eu_member=True)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


@extend_schema(
    tags=["Reference"],
    parameters=[
        OpenApiParameter(
            "parent",
            OpenApiTypes.INT,
            description="Cascading select: omit for top-level regions, pass a region id for its districts",
        )
    ],
)
class RegionListAPIView(_ReferenceListAPIView):
    serializer_class = RegionSerializer

    def get_queryset(self):
        parent = self.request.query_params.get("parent")
        if parent and parent.isdigit():
            return Region.objects.filter(parent_id=parent)
        return Region.objects.regions()


@extend_schema(
    tags=["Reference"],
    parameters=[
        OpenApiParameter("side", OpenApiTypes.STR, enum=["eu", "uz"]),
        OpenApiParameter("search", OpenApiTypes.STR, description="Autocomplete by name"),
    ],
)
class OrganizationListAPIView(_ReferenceListAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        queryset = Organization.objects.all()
        side = self.request.query_params.get("side")
        search = self.request.query_params.get("search")
        if side:
            queryset = queryset.filter(side=side)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset[:50] if search else queryset
