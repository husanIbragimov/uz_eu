import os

from .env import ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS, DEBUG

ALLOWED_HOSTS = ALLOWED_HOSTS if not DEBUG else ["*"]


# Credentials are needed for the HttpOnly refresh-token cookie, so origins are always an explicit
# allowlist (CORS_ALLOWED_ORIGINS in .env) — never allow-all, not even with DEBUG.
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS

CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS
