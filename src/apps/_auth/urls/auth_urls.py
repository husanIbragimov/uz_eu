from django.urls import path

from apps._auth.views import AuthAPIView, LogoutAPIView, RefreshAPIView

urlpatterns = [
    path("login/", view=AuthAPIView.as_view(), name="login_view"),
    path("refresh/", view=RefreshAPIView.as_view(), name="token_refresh"),
    path("logout/", view=LogoutAPIView.as_view(), name="user_logout"),
]
