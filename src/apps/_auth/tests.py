from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps._auth.models import User


class TokenRefreshAPITests(TestCase):
    def setUp(self):
        User.objects.create_user(username="refresher", password="s3cret-pass")
        self.client = APIClient()

    def _login(self) -> dict:
        response = self.client.post(
            reverse("auth:login_view"), {"username": "refresher", "password": "s3cret-pass"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_refresh_returns_new_pair_and_blacklists_old_refresh(self):
        tokens = self._login()

        response = self.client.post(reverse("auth:token_refresh"), {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertNotEqual(response.data["refresh"], tokens["refresh"])

        reused = self.client.post(reverse("auth:token_refresh"), {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_invalid_token(self):
        response = self.client.post(reverse("auth:token_refresh"), {"refresh": "not-a-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
