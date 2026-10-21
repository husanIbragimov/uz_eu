import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.audit.models import AuditLog
from apps.common.choices import UserRoleChoice
from apps.notifications.models import Notification, NotificationType
from apps.projects.models import Attachment, Subtask
from apps.projects.services.deadline_notifications import notify_approaching_deadlines
from apps.projects.tests.factories import client_for, make_project, make_user

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class TaskAPITests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.uz = make_user(UserRoleChoice.UZ_REPRESENTATIVE)
        self.eu = make_user(UserRoleChoice.EU_REPRESENTATIVE)
        self.project = make_project(self.uz)
        self.project.memberships.create(user=self.eu)
        self.main_task = self.project.main_tasks.first()
        self.deadline = (timezone.localdate() + timedelta(days=30)).isoformat()

    def create_subtask(self, client=None, **payload):
        payload = {"title": "Draft loan agreement", "deadline": self.deadline, **payload}
        url = reverse("workspace:subtasks", args=[self.main_task.pk])
        return (client or client_for(self.uz)).post(url, payload, format="json")

    # --- main tasks -----------------------------------------------------------------------------

    def test_main_task_list_is_public_and_derives_status(self):
        data = client_for().get(reverse("projects:main-tasks", args=[self.project.pk])).json()
        self.assertEqual(len(data), 10)
        self.assertEqual(data[0]["title"], "Negotiations")
        self.assertEqual((data[0]["status"], data[0]["subtask_count"]), ("pending", 0))

    def test_both_sides_can_add_rename_and_delete_main_tasks(self):
        url = reverse("projects:main-tasks", args=[self.project.pk])
        response = client_for(self.eu).post(url, {"title": "Environmental assessment"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task_id = response.json()["id"]
        self.assertEqual(response.json()["position"], 11)

        detail = reverse("workspace:main-task-detail", args=[task_id])
        self.assertEqual(client_for(self.uz).patch(detail, {"title": "ESIA"}, format="json").json()["title"], "ESIA")
        self.assertTrue(
            AuditLog.objects.filter(
                entity="maintask",
                entity_id=task_id,
                field="title",
                old_value="Environmental assessment",
                new_value="ESIA",
            ).exists()
        )
        self.assertEqual(client_for(self.uz).delete(detail).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(client_for().get(detail).status_code, status.HTTP_404_NOT_FOUND)

    def test_viewer_and_strangers_cannot_modify(self):
        url = reverse("projects:main-tasks", args=[self.project.pk])
        for user in (make_user(UserRoleChoice.VIEWER), make_user(UserRoleChoice.EU_REPRESENTATIVE)):
            self.assertEqual(client_for(user).post(url, {"title": "x"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.create_subtask(client_for(make_user())).status_code, status.HTTP_403_FORBIDDEN)

    def test_reorder_main_tasks(self):
        ids = list(self.project.main_tasks.values_list("pk", flat=True))
        new_order = list(reversed(ids))
        url = reverse("projects:main-tasks-reorder", args=[self.project.pk])
        response = client_for(self.uz).post(url, {"ids": new_order}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.json()], new_order)

        bad = client_for(self.uz).post(url, {"ids": new_order[:-1]}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ids", bad.json())

    # --- subtasks -------------------------------------------------------------------------------

    def test_deadline_is_required(self):
        response = self.create_subtask(deadline=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", response.json())

    def test_subtask_shape_and_indicator(self):
        response = self.create_subtask(client_for(self.eu))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        data = response.json()
        self.assertEqual(data["status"], "not_started")
        self.assertEqual(data["deadline_indicator"], "green")
        self.assertRegex(data["deadline_display"], r"^\d{2}\.\d{2}\.\d{4}$")

        soon = (timezone.localdate() + timedelta(days=2)).isoformat()
        self.assertEqual(self.create_subtask(deadline=soon).json()["deadline_indicator"], "yellow")

    def test_status_change_sets_completed_at_updates_main_task_and_notifies(self):
        subtask_id = self.create_subtask().json()["id"]
        url = reverse("workspace:subtask-detail", args=[subtask_id])

        data = client_for(self.eu).patch(url, {"status": "completed"}, format="json").json()
        self.assertEqual(data["status"], "completed")
        self.assertIsNotNone(data["completed_at"])
        self.assertEqual(data["deadline_indicator"], "green")

        main_tasks = client_for().get(reverse("projects:main-tasks", args=[self.project.pk])).json()
        self.assertEqual(main_tasks[0]["status"], "completed")

        notification = Notification.objects.get(user=self.uz, type=NotificationType.STATUS_CHANGE)
        self.assertEqual(notification.payload["new_status"], "completed")
        self.assertFalse(Notification.objects.filter(user=self.eu).exists())  # actor is not notified
        self.assertTrue(AuditLog.objects.filter(entity="subtask", field="status", new_value="completed").exists())

        data = client_for(self.eu).patch(url, {"status": "in_progress"}, format="json").json()
        self.assertIsNone(data["completed_at"])
        main_tasks = client_for().get(reverse("projects:main-tasks", args=[self.project.pk])).json()
        self.assertEqual(main_tasks[0]["status"], "in_progress")

    def test_delete_subtask_is_soft(self):
        subtask_id = self.create_subtask().json()["id"]
        url = reverse("workspace:subtask-detail", args=[subtask_id])
        self.assertEqual(client_for(self.uz).delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Subtask.all_objects.filter(pk=subtask_id, deleted_at__isnull=False).exists())
        self.assertTrue(AuditLog.objects.filter(entity="subtask", entity_id=subtask_id, action="delete").exists())

    # --- attachments ----------------------------------------------------------------------------

    def test_upload_and_delete_attachment(self):
        subtask_id = self.create_subtask().json()["id"]
        url = reverse("workspace:subtask-attachments", args=[subtask_id])
        upload = SimpleUploadedFile("site-plan.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = client_for(self.eu).post(url, {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual((response.json()["kind"], response.json()["file_name"]), ("pdf", "site-plan.pdf"))

        subtask = client_for().get(reverse("workspace:subtask-detail", args=[subtask_id])).json()
        self.assertEqual(len(subtask["attachments"]), 1)

        attachment_url = reverse("workspace:attachment-detail", args=[response.json()["id"]])
        self.assertEqual(client_for(self.uz).delete(attachment_url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertEqual(Attachment.all_objects.count(), 1)

    def test_rejects_disallowed_type(self):
        subtask_id = self.create_subtask().json()["id"]
        url = reverse("workspace:subtask-attachments", args=[subtask_id])
        upload = SimpleUploadedFile("run.exe", b"MZ", content_type="application/octet-stream")
        response = client_for(self.uz).post(url, {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.json())

    @override_settings(ATTACHMENT_MAX_SIZE_MB=0)
    def test_rejects_oversized_file(self):
        subtask_id = self.create_subtask().json()["id"]
        url = reverse("workspace:subtask-attachments", args=[subtask_id])
        upload = SimpleUploadedFile("photo.png", b"x" * 10, content_type="image/png")
        response = client_for(self.uz).post(url, {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- deadlines job --------------------------------------------------------------------------

    def test_approaching_deadline_notifications_are_deduplicated(self):
        soon = (timezone.localdate() + timedelta(days=3)).isoformat()
        self.create_subtask(deadline=soon)
        self.create_subtask(title="Far away")  # 30 days -> no notification
        notify_approaching_deadlines()
        notify_approaching_deadlines()
        deadline_notifications = Notification.objects.filter(type=NotificationType.DEADLINE)
        self.assertEqual(deadline_notifications.count(), 2)  # one per member
        self.assertEqual(deadline_notifications.first().payload["days_left"], 3)

    # --- search ---------------------------------------------------------------------------------

    def test_global_search(self):
        self.create_subtask(title="Turbine procurement")
        data = client_for().get(reverse("workspace:search"), {"q": "turbine"}).json()
        self.assertEqual(data["subtasks"][0]["title"], "Turbine procurement")
        self.assertEqual(client_for().get(reverse("workspace:search"), {"q": "a"}).status_code, 400)
