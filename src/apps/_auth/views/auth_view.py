from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from apps._auth.serializers.auth_serializer import AuthResponseSerializer
from apps._auth.services.auth_service import AuthService

AccessTokenResponse = inline_serializer("AccessToken", {"access": serializers.CharField()})


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(value=refresh_token, **settings.REFRESH_TOKEN_COOKIE)


def clear_refresh_cookie(response: Response) -> None:
    cookie = settings.REFRESH_TOKEN_COOKIE
    response.delete_cookie(cookie["key"], path=cookie["path"], domain=cookie["domain"], samesite=cookie["samesite"])


def get_refresh_cookie(request) -> str | None:
    return request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE["key"])


class AuthAPIView(GenericAPIView):
    """Login: `access` in the body, the refresh token in an HttpOnly cookie."""

    serializer_class = AuthResponseSerializer
    permission_classes = (permissions.AllowAny,)

    @extend_schema(tags=["Auth"], responses=AccessTokenResponse)
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        tokens = AuthService.auth_token(username, password)
        response = Response({"access": tokens["access"]}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, tokens["refresh"])
        return response


class RefreshAPIView(APIView):
    """Reads the refresh token from its cookie, returns a new `access` and rotates the cookie."""

    permission_classes = (permissions.AllowAny,)
    # an expired access token in the Authorization header must not block the refresh itself
    authentication_classes = ()

    def get_authenticate_header(self, request):
        # without authenticators DRF would downgrade AuthenticationFailed to 403; keep it a 401
        return 'Bearer realm="api"'

    @extend_schema(tags=["Auth"], request=None, responses=AccessTokenResponse)
    def post(self, request, *args, **kwargs):
        refresh_token = get_refresh_cookie(request)
        if not refresh_token:
            raise AuthenticationFailed("Refresh token cookie is missing.")

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e

        response = Response({"access": serializer.validated_data["access"]}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, serializer.validated_data.get("refresh", refresh_token))
        return response


@extend_schema(tags=["Auth"], request=None)
class LogoutAPIView(APIView):
    """Blacklists the refresh token from the cookie (if any) and deletes the cookie."""

    permission_classes = (permissions.IsAuthenticated,)
    service_class = AuthService()

    def post(self, request) -> Response:
        refresh_token = get_refresh_cookie(request)
        if refresh_token:
            try:
                self.service_class.logout(refresh_token)
            except AuthenticationFailed:
                # an already expired/blacklisted token needs no blacklisting; the cookie is cleared regardless
                pass
        response = Response(status=status.HTTP_205_RESET_CONTENT)
        clear_refresh_cookie(response)
        return response
