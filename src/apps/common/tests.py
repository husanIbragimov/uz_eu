import re
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase


class EnglishOnlyTests(SimpleTestCase):
    def test_only_english_locale(self):
        self.assertEqual(settings.LANGUAGE_CODE, "en")
        self.assertEqual([code for code, _ in settings.LANGUAGES], ["en"])
        self.assertNotIn("django.middleware.locale.LocaleMiddleware", settings.MIDDLEWARE)

    def test_legacy_language_prefixes_redirect_permanently(self):
        for prefix in ("ru", "uz", "RU"):
            response = self.client.get(f"/{prefix}/api/v1/projects/?category=ongoing")
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response["Location"], "/api/v1/projects/?category=ongoing")
        self.assertEqual(self.client.get("/uz")["Location"], "/")

    def test_similar_paths_are_not_redirected(self):
        response = self.client.get("/uzbekistan/")
        self.assertNotEqual(response.status_code, 301)

    def test_templates_contain_no_cyrillic(self):
        cyrillic = re.compile("[Ѐ-ӿ]")
        for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            self.assertIsNone(cyrillic.search(path.read_text(encoding="utf-8")), path)


class ReportMissingEnglishTests(TestCase):
    def test_runs_and_outputs_csv_header(self):
        out, err = StringIO(), StringIO()
        call_command("report_missing_english", stdout=out, stderr=err)
        self.assertTrue(out.getvalue().startswith("model,id,field"))
        self.assertIn("missing an English value", err.getvalue())
