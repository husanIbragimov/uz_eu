import json
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.projects.models import MainTask, Project, Subtask

EXPORT = {
    "projects": [
        {
            "id": "PMI-1",
            "name": "Wind farm",
            "category": "upcoming",
            "cost": 250,
            "sector": "Renewable Energy",
            "countries": ["de", "DK"],
            "region": "Navoi region",
            "district": "Tamdy",
            "initiator": "Ministry of Energy",
            "eu_partners": ["KfW Development Bank"],
            "uz_partners": ["Uzbekenergo JSC"],
            "stages": [
                {
                    "id": "S-1",
                    "title": "Negotiations",
                    "tasks": [
                        {
                            "id": "T-1",
                            "title": "MoU",
                            "deadline": "2026-01-10",
                            "status": "done",
                            "completed_at": "2026-01-09T10:00:00Z",
                        },
                        {"id": "T-2", "title": "No deadline"},
                    ],
                }
            ],
        },
        {"name": "No id"},
    ]
}


class PmiImportTests(TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            json.dump(EXPORT, fh)

    def tearDown(self):
        os.remove(self.path)

    def run_import(self, *args) -> str:
        out = StringIO()
        call_command("import_pmi", "--file", self.path, *args, stdout=out)
        return out.getvalue()

    def test_import_is_idempotent_and_reports(self):
        output = self.run_import()
        self.assertIn("projects_imported: 1", output)
        self.assertIn("subtasks_imported: 1", output)
        self.assertIn("missing or invalid deadline", output)
        self.assertIn("Project without id skipped", output)

        project = Project.objects.get(legacy_pmi_id="PMI-1")
        self.assertEqual(
            (project.category, project.district.name, project.region.name), ("upcoming", "Tamdy", "Navoi region")
        )
        self.assertEqual(sorted(project.countries.values_list("iso_code", flat=True)), ["DE", "DK"])
        self.assertEqual(project.main_tasks.count(), 1)  # PMI stages, not the default template
        subtask = Subtask.objects.get(legacy_pmi_id="T-1")
        self.assertEqual(subtask.status, "completed")
        self.assertIsNotNone(subtask.completed_at)

        output = self.run_import()
        self.assertIn("projects_skipped: 1", output)
        self.assertIn("subtasks_skipped: 1", output)
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(MainTask.objects.count(), 1)
        self.assertEqual(Subtask.objects.count(), 1)

    def test_dry_run_writes_nothing(self):
        output = self.run_import("--dry-run")
        self.assertIn("[DRY RUN] projects_imported: 1", output)
        self.assertEqual(Project.objects.count(), 0)
