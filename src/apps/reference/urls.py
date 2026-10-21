from django.urls import path

from apps.reference.views import CountryListAPIView, OrganizationListAPIView, RegionListAPIView, SectorListAPIView

urlpatterns = [
    path("sectors/", SectorListAPIView.as_view(), name="sectors"),
    path("countries/", CountryListAPIView.as_view(), name="countries"),
    path("regions/", RegionListAPIView.as_view(), name="regions"),
    path("organizations/", OrganizationListAPIView.as_view(), name="organizations"),
]
