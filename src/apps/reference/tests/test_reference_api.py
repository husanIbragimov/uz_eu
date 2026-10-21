from django.test import TestCase
from django.urls import reverse

from apps.reference.models import Region


class ReferenceAPITests(TestCase):
    """Seed data is loaded by the reference.0002 data migration."""

    def test_eu27_countries_with_flags(self):
        data = self.client.get(reverse("reference:countries")).json()
        self.assertEqual(len(data), 27)
        germany = next(row for row in data if row["iso_code"] == "DE")
        self.assertEqual(germany["flag"], "\U0001f1e9\U0001f1ea")

    def test_country_search(self):
        data = self.client.get(reverse("reference:countries"), {"search": "slov"}).json()
        self.assertEqual({row["iso_code"] for row in data}, {"SK", "SI"})

    def test_cascading_regions_and_districts(self):
        regions = self.client.get(reverse("reference:regions")).json()
        self.assertEqual(len(regions), 14)
        self.assertTrue(all(row["parent"] is None for row in regions))

        samarkand = Region.objects.get(name="Samarkand region")
        districts = self.client.get(reverse("reference:regions"), {"parent": samarkand.pk}).json()
        self.assertIn("Urgut", [row["name"] for row in districts])
        self.assertTrue(all(row["parent"] == samarkand.pk for row in districts))
        self.assertEqual(samarkand.children.count(), len(districts))

    def test_organization_autocomplete_by_side(self):
        data = self.client.get(reverse("reference:organizations"), {"side": "eu", "search": "kfw"}).json()
        self.assertEqual([row["name"] for row in data], ["KfW Development Bank"])

    def test_sectors(self):
        self.assertGreater(len(self.client.get(reverse("reference:sectors")).json()), 0)
