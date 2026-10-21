import itertools
from decimal import Decimal

from rest_framework.test import APIClient

from apps._auth.models import User
from apps.common.choices import UserRoleChoice
from apps.projects.choices import ProjectCategory
from apps.projects.services import ProjectService
from apps.reference.models import Country, Region, Sector

_counter = itertools.count(1)


def make_user(role=UserRoleChoice.UZ_REPRESENTATIVE, **extra) -> User:
    username = extra.pop("username", f"user{next(_counter)}")
    return User.objects.create_user(username=username, password="pass-12345", role=role, **extra)


def make_admin() -> User:
    return make_user(UserRoleChoice.ADMIN)


def client_for(user=None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def district(name="Urgut") -> Region:
    return Region.objects.districts().get(name=name)


def project_payload(**overrides) -> dict:
    """Valid API payload for POST /projects/."""
    payload = {
        "name": "Cement plant modernisation",
        "category": ProjectCategory.ONGOING,
        "cost": "120.50",
        "sector_id": Sector.objects.get(name="Construction Materials").pk,
        "country_ids": [Country.objects.get(iso_code="DE").pk, Country.objects.get(iso_code="FR").pk],
        "district_id": district().pk,
        "program": "Global Gateway",
        "initiator_name": "Ministry of Investment, Industry and Trade",
        "eu_partner_names": ["European Investment Bank (EIB)", "KfW Development Bank"],
        "uz_partner_names": ["Uzbekcement JSC"],
    }
    payload.update(overrides)
    return payload


def make_project(user=None, seed_default_tasks=True, **overrides):
    data = {
        "name": overrides.pop("name", "Project"),
        "category": overrides.pop("category", ProjectCategory.ONGOING),
        "cost": Decimal(str(overrides.pop("cost", "100.00"))),
        "sector": overrides.pop("sector", Sector.objects.get(name="Energy")),
        "countries": overrides.pop("countries", [Country.objects.get(iso_code="DE")]),
        "district": overrides.pop("district", district()),
        "eu_partner_names": overrides.pop("eu_partner_names", ["KfW Development Bank"]),
        "uz_partner_names": overrides.pop("uz_partner_names", ["Uzbekcement JSC"]),
        "initiator_name": overrides.pop("initiator_name", "Ministry of Energy"),
        **overrides,
    }
    return ProjectService.create(user, data, seed_default_tasks=seed_default_tasks)
