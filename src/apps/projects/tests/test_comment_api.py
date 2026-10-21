import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status

from apps.audit.models import AuditLog
from apps.common.choices import UserRoleChoice
from apps.notifications.models import Notification
from apps.projects.models import Comment
from apps.projects.tests.factories import client_for, make_admin, make_project, make_user

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class CommentAPITests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.uz = make_user(UserRoleChoice.UZ_REPRESENTATIVE, first_name="Aziz", last_name="Karimov")
        self.eu = make_user(UserRoleChoice.EU_REPRESENTATIVE, first_name="Anna", last_name="Schmidt")
        self.project = make_project(self.uz)
        self.project.memberships.create(user=self.eu)
        self.url = reverse("projects:comments", args=[self.project.pk])

    def post(self, user, **data):
        return client_for(user).post(self.url, data, format="multipart")

    def test_comment_with_files_side_badge_and_notification(self):
        image = SimpleUploadedFile("site.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        sheet = SimpleUploadedFile("budget.xlsx", b"PK", content_type="application/vnd.ms-excel")
        response = self.post(self.eu, body="Loan agreement signed.", files=[image, sheet])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        data = response.json()
        self.assertEqual(data["author"]["full_name"], "Anna Schmidt")
        self.assertEqual((data["side"], data["side_display"]), ("eu", "European side"))
        self.assertEqual(sorted(a["kind"] for a in data["attachments"]), ["image", "xls"])
        self.assertTrue(data["can_edit"])
        self.assertRegex(data["created_at_display"], r"^\d{2} \w{3} \d{4}, \d{2}:\d{2}$")

        self.assertTrue(Notification.objects.filter(user=self.uz, type="comment").exists())
        self.assertFalse(Notification.objects.filter(user=self.eu).exists())

    def test_empty_comment_rejected(self):
        response = self.post(self.uz, body="  ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("body", response.json())

    def test_filter_by_main_task(self):
        task = self.project.main_tasks.first()
        self.post(self.uz, body="general")
        self.post(self.uz, body="about negotiations", main_task=task.pk)
        data = client_for(self.uz).get(self.url, {"main_task": task.pk}).json()
        self.assertEqual([c["body"] for c in data["results"]], ["about negotiations"])
        self.assertEqual(client_for(self.uz).get(self.url).json()["count"], 2)

    def test_main_task_from_other_project_rejected(self):
        other = make_project(self.uz).main_tasks.first()
        response = self.post(self.uz, body="x", main_task=other.pk)
        self.assertIn("main_task", response.json())

    def test_viewers_and_guests_cannot_read_comments(self):
        self.post(self.uz, body="internal")
        self.assertEqual(client_for(make_user(UserRoleChoice.VIEWER)).get(self.url).status_code, 403)
        self.assertIn(client_for().get(self.url).status_code, (401, 403))

    def test_author_edits_within_window_with_history(self):
        comment_id = self.post(self.uz, body="first").json()["id"]
        url = reverse("workspace:comment-detail", args=[comment_id])
        data = client_for(self.uz).patch(url, {"body": "second"}, format="json").json()
        self.assertEqual((data["body"], data["is_edited"]), ("second", True))
        log = AuditLog.objects.get(entity="comment", entity_id=comment_id, field="body", action="update")
        self.assertEqual((log.old_value, log.new_value), ("first", "second"))

    def test_other_member_cannot_edit(self):
        comment_id = self.post(self.uz, body="first").json()["id"]
        url = reverse("workspace:comment-detail", args=[comment_id])
        self.assertEqual(client_for(self.eu).patch(url, {"body": "x"}, format="json").status_code, 403)
        self.assertEqual(client_for(self.eu).delete(url).status_code, 403)

    def test_edit_window_expires_but_admin_still_can(self):
        comment_id = self.post(self.uz, body="first").json()["id"]
        Comment.objects.filter(pk=comment_id).update(
            created_at=Comment.objects.get(pk=comment_id).created_at - timedelta(minutes=16)
        )
        url = reverse("workspace:comment-detail", args=[comment_id])
        self.assertEqual(client_for(self.uz).patch(url, {"body": "late"}, format="json").status_code, 403)
        self.assertEqual(client_for(make_admin()).delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Comment.all_objects.filter(pk=comment_id, deleted_at__isnull=False).exists())
