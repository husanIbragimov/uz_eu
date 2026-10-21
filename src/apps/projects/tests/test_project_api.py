from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from apps.audit.models import AuditLog
from apps.common.choices import UserRoleChoice
from apps.projects.choices import ProjectCategory
from apps.projects.models import CategoryHistory, MainTask, Project
from apps.projects.services import TaskService
from apps.projects.tests.factories import client_for, district, make_admin, make_project, make_user, project_payload
from apps.reference.models import Country, MainTaskTemplate, Sector


class ProjectStatsAPITests(TestCase):
    def setUp(self):
        user = make_user()
        make_project(user, category=ProjectCategory.ONGOING, cost="4000.00", seed_default_tasks=False)
        make_project(user, category=ProjectCategory.ONGOING, cost="820.00", seed_default_tasks=False)
        make_project(user, category=ProjectCategory.UPCOMING, cost="10.50", seed_default_tasks=False)
        make_project(user, category=ProjectCategory.POTENTIAL, cost="99.00", seed_default_tasks=False)
        deleted = make_project(user, category=ProjectCategory.ONGOING, cost="1.00", seed_default_tasks=False)
        deleted.soft_delete()

    def test_counts_and_sums_match_db_and_ignore_soft_deleted(self):
        response = client_for().get(reverse("projects:stats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total"], 4)
        self.assertEqual(
            data["by_category"]["ongoing"], {"count": 2, "total_cost": "4820.00", "total_cost_display": "4,820"}
        )
        self.assertEqual(data["by_category"]["upcoming"]["count"], 1)
        self.assertEqual(data["by_category"]["upcoming"]["total_cost"], "10.50")
        # potential: count only, no value card
        self.assertEqual(data["by_category"]["potential"], {"count": 1})

    def test_empty_category_reports_zero(self):
        Project.objects.filter(category=ProjectCategory.UPCOMING).update(category=ProjectCategory.ONGOING)
        data = client_for().get(reverse("projects:stats")).json()
        self.assertEqual(data["by_category"]["upcoming"], {"count": 0, "total_cost": "0.00", "total_cost_display": "0"})


class ProjectTableAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        de, fr = Country.objects.get(iso_code="DE"), Country.objects.get(iso_code="FR")
        self.alpha = make_project(
            self.user,
            name="Alpha water",
            cost="300",
            countries=[fr],
            sector=Sector.objects.get(name="Healthcare"),
            seed_default_tasks=False,
        )
        self.beta = make_project(self.user, name="Beta solar", cost="50", countries=[de], seed_default_tasks=False)
        self.gamma = make_project(
            self.user,
            name="Gamma rail",
            cost="999",
            countries=[de, fr],
            category=ProjectCategory.UPCOMING,
            seed_default_tasks=False,
        )
        self.url = reverse("projects:list")

    def test_filters_by_category(self):
        data = client_for().get(self.url, {"category": "ongoing"}).json()
        self.assertEqual(data["count"], 2)
        self.assertEqual({row["name"] for row in data["results"]}, {"Alpha water", "Beta solar"})

    def test_sort_by_cost_desc_with_row_numbers(self):
        data = client_for().get(self.url, {"sort": "cost", "order": "desc"}).json()
        self.assertEqual([row["name"] for row in data["results"]], ["Gamma rail", "Alpha water", "Beta solar"])
        self.assertEqual([row["row_number"] for row in data["results"]], [1, 2, 3])

    def test_sort_by_country_asc(self):
        data = client_for().get(self.url, {"sort": "country", "order": "asc", "category": "ongoing"}).json()
        self.assertEqual([row["country"] for row in data["results"]], ["France", "Germany"])

    def test_row_numbers_continue_across_pages(self):
        data = client_for().get(self.url, {"sort": "name", "order": "asc", "page": 2, "page_size": 2}).json()
        self.assertEqual(data["results"][0]["row_number"], 3)
        self.assertEqual(data["results"][0]["name"], "Gamma rail")

    def test_search_by_name_and_id(self):
        self.assertEqual(client_for().get(self.url, {"search": "solar"}).json()["count"], 1)
        data = client_for().get(self.url, {"search": self.gamma.code}).json()
        self.assertEqual([row["id"] for row in data["results"]], [self.gamma.pk])

    def test_filter_by_country_iso_and_sector(self):
        self.assertEqual(client_for().get(self.url, {"country": "fr"}).json()["count"], 2)
        sector = Sector.objects.get(name="Healthcare").pk
        self.assertEqual(client_for().get(self.url, {"sector": sector}).json()["count"], 1)

    def test_row_shape(self):
        row = client_for().get(self.url, {"search": "Gamma"}).json()["results"][0]
        self.assertEqual(row["project_id"], self.gamma.code)
        self.assertEqual(row["country"], "France, Germany")
        self.assertEqual(row["partner"], "KfW Development Bank")
        self.assertEqual(row["initiator"], "Ministry of Energy")
        self.assertEqual(row["cost_display"], "999")

    def test_invalid_sort_returns_field_error(self):
        response = client_for().get(self.url, {"sort": "bogus"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sort", response.json())

    def test_my_projects_only_lists_memberships(self):
        other = make_user(UserRoleChoice.EU_REPRESENTATIVE)
        make_project(other, name="Other", seed_default_tasks=False)
        data = client_for(other).get(reverse("projects:my")).json()
        self.assertEqual([row["name"] for row in data["results"]], ["Other"])


class ProjectCreateAPITests(TestCase):
    def test_representative_creates_project_with_default_tasks(self):
        user = make_user(UserRoleChoice.EU_REPRESENTATIVE)
        response = client_for(user).post(reverse("projects:list"), project_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        data = response.json()
        project = Project.objects.get(pk=data["id"])

        self.assertTrue(data["project_id"].startswith("UZEU-"))
        self.assertEqual(data["region"]["name"], "Samarkand region")
        self.assertEqual(
            data["breadcrumb"],
            ["Projects", "Global Gateway", "Samarkand region", "Urgut", "Ministry of Investment, Industry and Trade"],
        )
        self.assertTrue(project.memberships.filter(user=user).exists())
        self.assertEqual(
            list(project.main_tasks.values_list("title", flat=True)),
            list(MainTaskTemplate.objects.values_list("title", flat=True)),
        )
        self.assertEqual(project.main_tasks.count(), 10)
        self.assertTrue(AuditLog.objects.filter(entity="project", entity_id=project.pk, action="create").exists())
        self.assertEqual(CategoryHistory.objects.filter(project=project).count(), 1)

    def test_viewer_cannot_create(self):
        viewer = make_user(UserRoleChoice.VIEWER)
        response = client_for(viewer).post(reverse("projects:list"), project_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create(self):
        response = client_for().post(reverse("projects:list"), project_payload(), format="json")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_field_level_validation(self):
        user = make_user()
        payload = project_payload(cost="0", country_ids=[], eu_partner_names=[" "], district_id=district().parent_id)
        payload.pop("name")
        response = client_for(user).post(reverse("projects:list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()
        for field in ("name", "cost", "country_ids", "eu_partner_names", "district_id"):
            self.assertIn(field, errors)

    def test_non_eu_country_rejected(self):
        Country.objects.create(name="Norway", iso_code="NO", is_eu_member=False)
        payload = project_payload(country_ids=[Country.objects.get(iso_code="NO").pk])
        response = client_for(make_user()).post(reverse("projects:list"), payload, format="json")
        self.assertIn("country_ids", response.json())


class ProjectPassportAPITests(TestCase):
    def setUp(self):
        self.owner = make_user(UserRoleChoice.UZ_REPRESENTATIVE)
        self.project = make_project(self.owner)
        self.project.contacts.create(side="eu", full_name="Anna Schmidt", organization="KfW", phone="+4930123456")
        self.url = reverse("projects:detail", args=[self.project.pk])

    def test_viewer_does_not_see_contacts(self):
        viewer = make_user(UserRoleChoice.VIEWER)
        for client in (client_for(viewer), client_for()):
            data = client.get(self.url).json()
            self.assertNotIn("contacts", data)
            self.assertFalse(data["can_edit"])

    def test_member_sees_contacts_grouped_by_side(self):
        data = client_for(self.owner).get(self.url).json()
        self.assertEqual(data["contacts"]["eu"][0]["full_name"], "Anna Schmidt")
        self.assertEqual(data["contacts"]["uz"], [])
        self.assertTrue(data["can_edit"])

    def test_atomic_passport_save_updates_fields_and_contacts_with_audit(self):
        existing = self.project.contacts.get()
        payload = {
            "name": "Renamed",
            "cost": "4820",
            "contacts": [
                {"id": existing.pk, "side": "eu", "full_name": "Anna Schmidt", "organization": "KfW Bank"},
                {
                    "side": "uz",
                    "full_name": "Aziz Karimov",
                    "organization": "Uzbekcement JSC",
                    "email": "aziz@example.uz",
                    "phone": "+998 90 123 45 67",
                },
            ],
        }
        response = client_for(self.owner).patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        data = response.json()
        self.assertEqual(data["name"], "Renamed")
        self.assertEqual(data["cost_display"], "4,820")
        self.assertEqual(data["contacts"]["uz"][0]["phone"], "+998901234567")
        self.assertEqual(data["contacts"]["eu"][0]["organization"], "KfW Bank")

        name_log = AuditLog.objects.get(entity="project", entity_id=self.project.pk, field="name", action="update")
        self.assertEqual((name_log.old_value, name_log.new_value, name_log.user), ("Project", "Renamed", self.owner))
        self.assertTrue(
            AuditLog.objects.filter(entity="projectcontact", field="organization", old_value="KfW").exists()
        )

    def test_invalid_contact_rolls_back_whole_save(self):
        payload = {
            "name": "Should not persist",
            "contacts": [{"side": "uz", "full_name": "X", "organization": "Y", "email": "bad", "phone": "998"}],
        }
        response = client_for(self.owner).patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json()["contacts"][0])
        self.assertIn("phone", response.json()["contacts"][0])
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Project")

    def test_omitted_contact_is_soft_deleted(self):
        response = client_for(self.owner).patch(self.url, {"contacts": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.project.contacts.count(), 0)
        self.assertEqual(self.project.contacts.model.all_objects.filter(project=self.project).count(), 1)

    def test_foreign_contact_id_rejected(self):
        other = make_project(self.owner, seed_default_tasks=False)
        foreign = other.contacts.create(side="eu", full_name="Z", organization="Z")
        payload = {"contacts": [{"id": foreign.pk, "side": "eu", "full_name": "Z", "organization": "Z"}]}
        response = client_for(self.owner).patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_member_cannot_edit(self):
        stranger = make_user(UserRoleChoice.EU_REPRESENTATIVE)
        response = client_for(stranger).patch(self.url, {"name": "Hack"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_category_cannot_change_through_passport(self):
        response = client_for(self.owner).patch(self.url, {"category": "potential"}, format="json")
        self.assertIn("category", response.json())

    def test_only_admin_deletes_and_delete_is_soft(self):
        self.assertEqual(client_for(self.owner).delete(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_for(make_admin()).delete(self.url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(Project.all_objects.filter(pk=self.project.pk, deleted_at__isnull=False).exists())
        self.assertEqual(client_for().get(self.url).status_code, status.HTTP_404_NOT_FOUND)


class ProjectCategoryAPITests(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.project = make_project(self.owner)
        main_task = self.project.main_tasks.first()
        TaskService.create_subtask(self.owner, main_task, {"title": "Sign MoU", "deadline": "2026-05-01"})
        self.url = reverse("projects:category", args=[self.project.pk])

    def test_change_category_keeps_related_data_and_logs_history(self):
        response = client_for(self.owner).patch(self.url, {"category": "upcoming"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()["category"], "upcoming")
        self.assertEqual(MainTask.objects.filter(project=self.project).count(), 10)
        self.assertEqual(self.project.main_tasks.first().subtasks.count(), 1)

        history = CategoryHistory.objects.filter(project=self.project).first()
        self.assertEqual(
            (history.from_category, history.to_category, history.changed_by), ("ongoing", "upcoming", self.owner)
        )
        self.assertTrue(AuditLog.objects.filter(entity="project", field="category", new_value="upcoming").exists())

        history_data = client_for(self.owner).get(reverse("projects:category-history", args=[self.project.pk])).json()
        self.assertEqual(history_data[0]["to_category"], "upcoming")

    def test_invalid_category(self):
        response = client_for(self.owner).patch(self.url, {"category": "archived"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.json())

    def test_non_member_forbidden(self):
        response = client_for(make_user()).patch(self.url, {"category": "upcoming"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.project.refresh_from_db()
        self.assertEqual(self.project.category, "ongoing")


class ProjectMembersAndAuditAPITests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.owner = make_user()
        self.project = make_project(self.owner, seed_default_tasks=False)

    def test_admin_assigns_member_who_then_can_edit(self):
        eu = make_user(UserRoleChoice.EU_REPRESENTATIVE)
        url = reverse("projects:members", args=[self.project.pk])
        self.assertEqual(client_for(self.owner).post(url, {"user_id": eu.pk}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_for(self.admin).post(url, {"user_id": eu.pk}).status_code, status.HTTP_201_CREATED)

        detail = reverse("projects:detail", args=[self.project.pk])
        self.assertEqual(client_for(eu).patch(detail, {"cost": "5"}, format="json").status_code, 200)
        self.assertEqual(self.project.__class__.objects.get(pk=self.project.pk).cost, Decimal("5.00"))

        remove = reverse("projects:member-delete", args=[self.project.pk, eu.pk])
        self.assertEqual(client_for(self.admin).delete(remove).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(client_for(eu).patch(detail, {"cost": "6"}, format="json").status_code, 403)

    def test_project_audit_log_visible_to_members_only(self):
        url = reverse("projects:audit-log", args=[self.project.pk])
        self.assertEqual(client_for(self.owner).get(url).status_code, status.HTTP_200_OK)
        self.assertGreater(client_for(self.owner).get(url).json()["count"], 0)
        self.assertEqual(client_for(make_user(UserRoleChoice.VIEWER)).get(url).status_code, 403)

    def test_global_audit_log_admin_only(self):
        url = reverse("audit:list")
        self.assertEqual(client_for(self.owner).get(url).status_code, status.HTTP_403_FORBIDDEN)
        response = client_for(self.admin).get(url, {"entity": "project"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(row["entity"] == "project" for row in response.json()["results"]))
