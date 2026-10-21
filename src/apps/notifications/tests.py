from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from apps.notifications.models import Notification, NotificationType
from apps.projects.tests.factories import client_for, make_user


class NotificationAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user()
        for _ in range(3):
            Notification.objects.create(user=self.user, type=NotificationType.COMMENT, payload={"project_id": 1})
        Notification.objects.create(user=self.other, type=NotificationType.COMMENT)

    def test_list_only_own(self):
        data = client_for(self.user).get(reverse("notifications:list")).json()
        self.assertEqual(data["count"], 3)

    def test_unread_count_and_mark_read(self):
        client = client_for(self.user)
        self.assertEqual(client.get(reverse("notifications:unread-count")).json(), {"count": 3})

        notification = Notification.objects.filter(user=self.user).first()
        response = client.post(reverse("notifications:read", args=[notification.pk]))
        self.assertTrue(response.json()["is_read"])
        self.assertEqual(client.get(reverse("notifications:unread-count")).json(), {"count": 2})
        self.assertEqual(client.get(reverse("notifications:list"), {"unread": "true"}).json()["count"], 2)

        self.assertEqual(client.post(reverse("notifications:read-all")).json(), {"updated": 2})
        self.assertEqual(client.get(reverse("notifications:unread-count")).json(), {"count": 0})

    def test_cannot_read_someone_elses(self):
        foreign = Notification.objects.get(user=self.other)
        response = client_for(self.user).post(reverse("notifications:read", args=[foreign.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_auth(self):
        self.assertIn(client_for().get(reverse("notifications:list")).status_code, (401, 403))
