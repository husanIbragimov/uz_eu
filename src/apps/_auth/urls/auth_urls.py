from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from apps._auth.views import AuthAPIView, LogoutAPIView

urlpatterns = [
    path("login/", view=AuthAPIView.as_view(), name="login_view"),
    path(
        "refresh/",
        view=extend_schema_view(post=extend_schema(tags=["Auth"]))(TokenRefreshView).as_view(),
        name="token_refresh",
    ),
    path("logout/", view=LogoutAPIView.as_view(), name="user_logout"),
]
