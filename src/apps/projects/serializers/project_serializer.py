from decimal import Decimal

from rest_framework import serializers

from apps._auth.serializers.userme_serializer import UserShortSerializer
from apps.common.choices import SideChoice
from apps.common.utils.formatting import format_deadline, format_money, format_timestamp
from apps.projects.choices import ProjectCategory, ProjectStatus
from apps.projects.models import CategoryHistory, Project, ProjectMember
from apps.projects.permissions import can_edit_project, can_view_private
from apps.projects.serializers.contact_serializer import NestedProjectContactSerializer, ProjectContactSerializer
from apps.reference.models import Country, Region, Sector
from apps.reference.serializers import CountrySerializer, OrganizationSerializer, RegionSerializer, SectorSerializer

# public sort key -> ORM ordering expression (annotations are added in the view)
PROJECT_SORT_FIELDS = {
    "project_id": "code",
    "name": "name",
    "sector": "sector__name",
    "country": "country_sort",
    "cost": "cost",
    "partner": "partner_sort",
    "initiator": "initiator__name",
    "status": "status",
    "category": "category",
    "updated": "updated_at",
}


class ProjectListQuerySerializer(serializers.Serializer):
    """Validates the query string of GET /projects/ so bad params return field-level errors."""

    category = serializers.ChoiceField(choices=ProjectCategory.choices, required=False)
    search = serializers.CharField(required=False, allow_blank=True)
    sector = serializers.IntegerField(required=False)
    country = serializers.CharField(required=False, help_text="Country id or ISO code")
    initiator = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=False)
    region = serializers.IntegerField(required=False)
    district = serializers.IntegerField(required=False)
    sort = serializers.ChoiceField(choices=list(PROJECT_SORT_FIELDS), default="updated")
    order = serializers.ChoiceField(choices=["asc", "desc"], default="desc")


class ProjectListSerializer(serializers.ModelSerializer):
    """Row of the projects table (Task 4)."""

    project_id = serializers.CharField(source="code", read_only=True)
    sector = serializers.CharField(source="sector.name", default=None, read_only=True)
    country = serializers.SerializerMethodField()
    cost_display = serializers.SerializerMethodField()
    partner = serializers.SerializerMethodField()
    initiator = serializers.CharField(source="initiator.name", default=None, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    updated_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id",
            "project_id",
            "name",
            "category",
            "category_display",
            "sector",
            "country",
            "cost",
            "cost_display",
            "partner",
            "initiator",
            "status",
            "status_display",
            "updated_at",
            "updated_at_display",
        )
        read_only_fields = fields

    def get_country(self, obj) -> str:
        return ", ".join(country.name for country in obj.countries.all())

    def get_partner(self, obj) -> str:
        return ", ".join(organization.name for organization in obj.eu_partners.all())

    def get_cost_display(self, obj) -> str:
        return format_money(obj.cost)

    def get_updated_at_display(self, obj) -> str:
        return format_deadline(obj.updated_at.date()) if obj.updated_at else ""


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Project Passport: read representation + write (create / atomic edit of both blocks)."""

    project_id = serializers.CharField(source="code", read_only=True)
    category = serializers.ChoiceField(choices=ProjectCategory.choices)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    cost = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    cost_display = serializers.SerializerMethodField()

    sector = SectorSerializer(read_only=True)
    sector_id = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.all(), source="sector", write_only=True)
    countries = CountrySerializer(many=True, read_only=True)
    country_ids = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.filter(is_eu_member=True),
        source="countries",
        many=True,
        allow_empty=False,
        write_only=True,
    )
    region = serializers.SerializerMethodField()
    district = RegionSerializer(read_only=True)
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.districts(), source="district", write_only=True
    )
    initiator = OrganizationSerializer(read_only=True)
    initiator_name = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    eu_partners = OrganizationSerializer(many=True, read_only=True)
    eu_partner_names = serializers.ListField(
        child=serializers.CharField(max_length=255), allow_empty=False, write_only=True
    )
    uz_partners = OrganizationSerializer(many=True, read_only=True)
    uz_partner_names = serializers.ListField(
        child=serializers.CharField(max_length=255), allow_empty=False, write_only=True
    )
    contacts = NestedProjectContactSerializer(many=True, write_only=True, required=False)

    breadcrumb = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    updated_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id",
            "project_id",
            "name",
            "category",
            "category_display",
            "status",
            "status_display",
            "cost",
            "cost_display",
            "sector",
            "sector_id",
            "countries",
            "country_ids",
            "region",
            "district",
            "district_id",
            "program",
            "initiator",
            "initiator_name",
            "eu_partners",
            "eu_partner_names",
            "uz_partners",
            "uz_partner_names",
            "description",
            "contacts",
            "legacy_pmi_id",
            "breadcrumb",
            "can_edit",
            "created_at",
            "updated_at",
            "updated_at_display",
        )
        read_only_fields = ("legacy_pmi_id", "created_at", "updated_at")

    @property
    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def validate_category(self, value):
        if self.instance is not None and value != self.instance.category:
            raise serializers.ValidationError("Use PATCH /projects/{id}/category/ to change the category.")
        return value

    def _clean_names(self, value: list[str]) -> list[str]:
        names = [name.strip() for name in value if name.strip()]
        if not names:
            raise serializers.ValidationError("At least one organization is required.")
        return names

    def validate_eu_partner_names(self, value):
        return self._clean_names(value)

    def validate_uz_partner_names(self, value):
        return self._clean_names(value)

    def validate_contacts(self, value):
        existing_ids = set(self.instance.contacts.values_list("id", flat=True)) if self.instance else set()
        for index, item in enumerate(value):
            contact_id = item.get("id")
            if contact_id and contact_id not in existing_ids:
                raise serializers.ValidationError({index: {"id": ["Contact does not belong to this project."]}})
        return value

    def get_cost_display(self, obj) -> str:
        return format_money(obj.cost)

    def get_region(self, obj) -> dict | None:
        region = obj.region
        return {"id": region.pk, "name": region.name} if region else None

    def get_breadcrumb(self, obj) -> list[str]:
        """Projects / {Program} / {Region} / {District} / {Initiator} (empty levels skipped)."""
        region = obj.region
        parts = [
            "Projects",
            obj.program,
            region.name if region else "",
            obj.district.name if obj.district_id else "",
            obj.initiator.name if obj.initiator_id else "",
        ]
        return [part for part in parts if part]

    def get_can_edit(self, obj) -> bool:
        return can_edit_project(self._user, obj)

    def get_updated_at_display(self, obj) -> str:
        return format_timestamp(obj.updated_at)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Contacts are never shown to viewers / guests.
        if can_view_private(self._user, instance):
            contacts = ProjectContactSerializer(instance.contacts.all(), many=True).data
            data["contacts"] = {
                SideChoice.EU.value: [contact for contact in contacts if contact["side"] == SideChoice.EU],
                SideChoice.UZ.value: [contact for contact in contacts if contact["side"] == SideChoice.UZ],
            }
        return data


class ProjectCategorySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=ProjectCategory.choices)


class CategoryStatsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=16, decimal_places=2, required=False)
    total_cost_display = serializers.CharField(required=False)


class ProjectStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_category = serializers.DictField(child=CategoryStatsSerializer())


class CategoryHistorySerializer(serializers.ModelSerializer):
    changed_by = UserShortSerializer(read_only=True)
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = CategoryHistory
        fields = ("id", "from_category", "to_category", "changed_by", "created_at", "created_at_display")

    def get_created_at_display(self, obj) -> str:
        return format_timestamp(obj.created_at)


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProjectMember
        fields = ("id", "user", "user_id", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_user_id(self, value):
        from apps._auth.models import User

        if not User.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("User not found.")
        return value
