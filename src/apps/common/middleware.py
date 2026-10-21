import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class LegacyLanguagePrefixRedirectMiddleware:
    """301-redirect old language-prefixed URLs (`/ru/...`, `/uz/...`) to their English equivalent."""

    def __init__(self, get_response):
        self.get_response = get_response
        prefixes = "|".join(re.escape(p) for p in settings.LEGACY_LANGUAGE_PREFIXES)
        self.pattern = re.compile(rf"^/(?:{prefixes})(?=/|$)", re.IGNORECASE)

    def __call__(self, request):
        match = self.pattern.match(request.path)
        if match:
            prefix_end = match.end()
            target = request.path[prefix_end:] or "/"
            query = request.META.get("QUERY_STRING")
            if query:
                target = f"{target}?{query}"
            return HttpResponsePermanentRedirect(target)
        return self.get_response(request)
