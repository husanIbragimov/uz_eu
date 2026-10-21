from rest_framework import serializers

from apps.reference.models import Country, Organization, Region, Sector


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ("id", "name")


class CountrySerializer(serializers.ModelSerializer):
    flag = serializers.CharField(read_only=True)

    class Meta:
        model = Country
        fields = ("id", "name", "iso_code", "flag")


class RegionSerializer(serializers.ModelSerializer):
    """A region (parent = null) or a district (parent = its region id)."""

    class Meta:
        model = Region
        fields = ("id", "name", "parent")


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "side")
