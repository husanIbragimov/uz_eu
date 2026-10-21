import sys

from .apps import INSTALLED_APPS
from .env import DEBUG
from .middleware import MIDDLEWARE

# silk records every request in the DB; keep it out of test runs (SimpleTestCase forbids DB access)
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if DEBUG and not TESTING:
    INSTALLED_APPS.append("silk")
    MIDDLEWARE.append("silk.middleware.SilkyMiddleware")
    INTERNAL_IPS = [
        "127.0.0.1",
        "0.0.0.0",
    ]
