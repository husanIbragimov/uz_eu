# The platform is English-only: no language switcher, no other locales.
LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
]

# Old language-prefixed URLs (/ru/..., /uz/...) are 301-redirected to the unprefixed
# English URL by apps.common.middleware.LegacyLanguagePrefixRedirectMiddleware.
LEGACY_LANGUAGE_PREFIXES = ["ru", "uz", "en"]

TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True

USE_TZ = True
