from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps._auth.models import User

COOKIE = settings.REFRESH_TOKEN_COOKIE["key"]


class RefreshCookieAPITests(TestCase):
    def setUp(self):
        User.objects.create_user(username="refresher", password="s3cret-pass")
        self.client = APIClient()

    def _login(self):
        response = self.client.post(
            reverse("auth:login_view"), {"username": "refresher", "password": "s3cret-pass"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_login_sets_httponly_cookie_and_hides_refresh_from_body(self):
        response = self._login()

        self.assertEqual(set(response.data), {"access"})
        cookie = response.cookies[COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/api/v1/auth/")
        self.assertEqual(cookie["samesite"], settings.REFRESH_TOKEN_COOKIE["samesite"])

    def test_refresh_rotates_cookie_and_rejects_reuse_of_old_token(self):
        old_refresh = self._login().cookies[COOKIE].value

        response = self.client.post(reverse("auth:token_refresh"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {"access"})
        new_refresh = response.cookies[COOKIE].value
        self.assertNotEqual(new_refresh, old_refresh)

        self.client.cookies[COOKIE] = old_refresh
        reused = self.client.post(reverse("auth:token_refresh"))
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_without_cookie_is_unauthorized(self):
        response = self.client.post(reverse("auth:token_refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_with_invalid_cookie_is_unauthorized(self):
        self.client.cookies[COOKIE] = "not-a-token"
        response = self.client.post(reverse("auth:token_refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_token_and_clears_cookie(self):
        response = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        logout = self.client.post(reverse("auth:user_logout"))
        self.assertEqual(logout.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(logout.cookies[COOKIE].value, "")
        self.assertEqual(BlacklistedToken.objects.count(), 1)
